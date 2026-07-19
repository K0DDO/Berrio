import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class StatementUploadResult {
  StatementUploadResult({required this.messages});

  final List<String> messages;

  factory StatementUploadResult.fromResponse(dynamic data) {
    if (data is List) {
      return StatementUploadResult(
        messages: data.map((e) {
          if (e is Map) {
            return e['message']?.toString() ??
                e['detail']?.toString() ??
                e.toString();
          }
          return e.toString();
        }).toList(),
      );
    }
    if (data is Map) {
      final map = Map<String, dynamic>.from(data);
      final raw = map['messages'] ??
          map['reconciliation'] ??
          map['items'] ??
          map['results'];
      if (raw is List) {
        return StatementUploadResult.fromResponse(raw);
      }
      if (map['message'] != null) {
        return StatementUploadResult(messages: [map['message'].toString()]);
      }
      if (map['detail'] != null) {
        return StatementUploadResult(messages: [map['detail'].toString()]);
      }
    }
    return StatementUploadResult(
      messages: data == null ? const [] : [data.toString()],
    );
  }
}

class BanksApi {
  BanksApi(this._dio);

  final Dio _dio;

  /// Multipart upload — backend path may land in parallel: POST /banks/statements/upload
  Future<StatementUploadResult> uploadStatement({
    required String bankCode,
    required String filePath,
    required String fileName,
  }) async {
    final form = FormData.fromMap({
      'bank_code': bankCode,
      'file': await MultipartFile.fromFile(filePath, filename: fileName),
    });
    final response = await _dio.post<dynamic>(
      '/banks/statements/upload',
      data: form,
    );
    return StatementUploadResult.fromResponse(response.data);
  }
}

final banksApiProvider = Provider<BanksApi>((ref) {
  return BanksApi(ref.watch(dioProvider));
});
