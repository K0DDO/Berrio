import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class ReceiptItemDto {
  ReceiptItemDto({
    required this.id,
    required this.nameRaw,
    required this.qty,
    required this.price,
    required this.sum,
    this.categoryId,
    this.categoryName,
    this.productVariantId,
    this.priceChangePct,
    this.previousPrice,
  });

  final String id;
  final String nameRaw;
  final String qty;
  final String price;
  final String sum;
  final String? categoryId;
  final String? categoryName;
  final String? productVariantId;
  final double? priceChangePct;
  final String? previousPrice;

  factory ReceiptItemDto.fromJson(Map<String, dynamic> json) {
    return ReceiptItemDto(
      id: json['id'] as String,
      nameRaw: json['name_raw'] as String? ?? '',
      qty: json['qty']?.toString() ?? '1',
      price: json['price']?.toString() ?? '0',
      sum: json['sum']?.toString() ?? '0',
      categoryId: json['category_id']?.toString(),
      categoryName: json['category_name'] as String?,
      productVariantId: json['product_variant_id']?.toString(),
      priceChangePct: (json['price_change_pct'] as num?)?.toDouble(),
      previousPrice: json['previous_price']?.toString(),
    );
  }
}

class ReceiptDto {
  ReceiptDto({
    required this.id,
    required this.fn,
    required this.fd,
    required this.fp,
    required this.status,
    this.storeName,
    this.totalAmount,
    this.purchasedAt,
    this.errorMessage,
    this.items = const [],
  });

  final String id;
  final String fn;
  final String fd;
  final String fp;
  final String status;
  final String? storeName;
  final String? totalAmount;
  final DateTime? purchasedAt;
  final String? errorMessage;
  final List<ReceiptItemDto> items;

  factory ReceiptDto.fromJson(Map<String, dynamic> json) {
    return ReceiptDto(
      id: json['id'] as String,
      fn: json['fn'] as String,
      fd: json['fd'] as String,
      fp: json['fp'] as String,
      status: json['status'] as String,
      storeName: json['store_name'] as String?,
      totalAmount: json['total_amount']?.toString(),
      purchasedAt: json['purchased_at'] != null
          ? DateTime.tryParse(json['purchased_at'] as String)
          : null,
      errorMessage: json['error_message'] as String?,
      items: (json['items'] as List<dynamic>? ?? [])
          .map((e) => ReceiptItemDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }
}

class ReceiptsApi {
  ReceiptsApi(this._dio);

  final Dio _dio;

  Future<ReceiptDto> scan(Map<String, dynamic> payload) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/receipts/scan',
      data: {
        'fn': payload['fn'],
        'fd': payload['fd'],
        'fp': payload['fp'],
        if (payload['total_amount'] != null) 'total_amount': payload['total_amount'],
        if (payload['purchased_at'] != null) 'purchased_at': payload['purchased_at'],
        if (payload['qrraw'] != null) 'qrraw': payload['qrraw'],
        if (payload['idempotency_key'] != null)
          'idempotency_key': payload['idempotency_key'],
      },
    );
    return ReceiptDto.fromJson(response.data!);
  }

  Future<List<ReceiptDto>> list() async {
    final response = await _dio.get<Map<String, dynamic>>('/receipts');
    final items = response.data?['items'] as List<dynamic>? ?? [];
    return items
        .map((e) => ReceiptDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<ReceiptDto> getById(String id) async {
    final response = await _dio.get<Map<String, dynamic>>('/receipts/$id');
    return ReceiptDto.fromJson(response.data!);
  }
}

final receiptsApiProvider = Provider<ReceiptsApi>((ref) {
  return ReceiptsApi(ref.watch(dioProvider));
});

final receiptsListProvider = FutureProvider.autoDispose<List<ReceiptDto>>((ref) {
  return ref.watch(receiptsApiProvider).list();
});

final receiptDetailProvider =
    FutureProvider.autoDispose.family<ReceiptDto, String>((ref, id) {
  return ref.watch(receiptsApiProvider).getById(id);
});
