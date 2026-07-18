import 'package:dio/dio.dart';

class ReceiptDto {
  ReceiptDto({
    required this.id,
    required this.fn,
    required this.fd,
    required this.fp,
    required this.status,
    this.storeName,
    this.totalAmount,
    this.items = const [],
  });

  final String id;
  final String fn;
  final String fd;
  final String fp;
  final String status;
  final String? storeName;
  final String? totalAmount;
  final List<Map<String, dynamic>> items;

  factory ReceiptDto.fromJson(Map<String, dynamic> json) {
    return ReceiptDto(
      id: json['id'] as String,
      fn: json['fn'] as String,
      fd: json['fd'] as String,
      fp: json['fp'] as String,
      status: json['status'] as String,
      storeName: json['store_name'] as String?,
      totalAmount: json['total_amount']?.toString(),
      items: (json['items'] as List<dynamic>? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
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
}
