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
    this.nameDisplay,
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
  final String? nameDisplay;
  final String? categoryId;
  final String? categoryName;
  final String? productVariantId;
  final double? priceChangePct;
  final String? previousPrice;

  factory ReceiptItemDto.fromJson(Map<String, dynamic> json) {
    return ReceiptItemDto(
      id: json['id'] as String,
      nameRaw: json['name_raw'] as String? ?? '',
      nameDisplay: json['name_display'] as String?,
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
    this.requiresConfirmation = false,
    this.warnings = const [],
    this.recognition,
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
  final bool requiresConfirmation;
  final List<String> warnings;
  final Map<String, dynamic>? recognition;
  final List<ReceiptItemDto> items;

  factory ReceiptDto.fromJson(Map<String, dynamic> json) {
    final recognitionRaw = json['recognition'];
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
      requiresConfirmation: json['requires_confirmation'] as bool? ?? false,
      warnings: (json['warnings'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      recognition: recognitionRaw is Map
          ? Map<String, dynamic>.from(recognitionRaw)
          : null,
      items: (json['items'] as List<dynamic>? ?? [])
          .map((e) => ReceiptItemDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
    );
  }
}

class ReceiptConfirmPayload {
  ReceiptConfirmPayload({
    this.storeName,
    this.totalAmount,
    this.purchasedAt,
    this.items = const [],
    this.confirmAsIs = false,
    this.saveAsDraft = false,
    this.dateIgnored = false,
    this.dateConfirmed = false,
  });

  final String? storeName;
  final String? totalAmount;
  final String? purchasedAt;
  final List<ReceiptConfirmItemPayload> items;
  final bool confirmAsIs;
  final bool saveAsDraft;
  final bool dateIgnored;
  final bool dateConfirmed;

  Map<String, dynamic> toJson() => {
        if (storeName != null) 'store_name': storeName,
        if (totalAmount != null) 'total_amount': totalAmount,
        if (purchasedAt != null) 'purchased_at': purchasedAt,
        'items': items.map((e) => e.toJson()).toList(),
        'confirm_as_is': confirmAsIs,
        'save_as_draft': saveAsDraft,
        'date_ignored': dateIgnored,
        'date_confirmed': dateConfirmed,
      };
}

class ReceiptConfirmItemPayload {
  ReceiptConfirmItemPayload({
    required this.name,
    required this.qty,
    required this.price,
    required this.sum,
    this.categorySlug,
    this.nameDisplay,
  });

  final String name;
  final String qty;
  final String price;
  final String sum;
  final String? categorySlug;
  final String? nameDisplay;

  Map<String, dynamic> toJson() => {
        'name': name,
        'qty': qty,
        'price': price,
        'sum': sum,
        if (categorySlug != null) 'category_slug': categorySlug,
        if (nameDisplay != null) 'name_display': nameDisplay,
      };
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

  Future<ReceiptDto> confirm(String receiptId, ReceiptConfirmPayload payload) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/receipts/$receiptId/confirm',
      data: payload.toJson(),
    );
    return ReceiptDto.fromJson(response.data!);
  }

  /// OCR / pasted text → server structures receipt (photos never uploaded).
  Future<AnalyzeTextResult> analyzeText(String rawText, {bool persist = true}) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/receipts/analyze-text',
      data: {'raw_text': rawText, 'persist': persist},
    );
    final data = response.data!;
    return AnalyzeTextResult(
      success: data['success'] as bool? ?? false,
      requiresConfirmation: data['requires_confirmation'] as bool? ?? true,
      reason: data['reason'] as String?,
      receiptId: data['receipt_id']?.toString(),
      status: data['status'] as String?,
      warnings: (data['warnings'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
    );
  }
}

class AnalyzeTextResult {
  AnalyzeTextResult({
    required this.success,
    required this.requiresConfirmation,
    this.reason,
    this.receiptId,
    this.status,
    this.warnings = const [],
  });

  final bool success;
  final bool requiresConfirmation;
  final String? reason;
  final String? receiptId;
  final String? status;
  final List<String> warnings;
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
