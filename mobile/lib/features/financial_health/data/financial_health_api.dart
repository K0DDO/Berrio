import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../analytics/data/analytics_api.dart';

class FinancialHealthDto {
  FinancialHealthDto({
    required this.score,
    required this.factors,
  });

  final int score;
  final ScoreFactorsDto factors;

  factory FinancialHealthDto.fromJson(Map<String, dynamic> json) {
    final factorsRaw = json['factors'];
    return FinancialHealthDto(
      score: json['score'] as int? ?? 0,
      factors: factorsRaw is Map
          ? ScoreFactorsDto.fromJson(Map<String, dynamic>.from(factorsRaw))
          : ScoreFactorsDto(positive: const [], negative: const []),
    );
  }
}

class FinancialHealthApi {
  FinancialHealthApi(this._dio);

  final Dio _dio;

  Future<FinancialHealthDto> score() async {
    final response = await _dio.get<Map<String, dynamic>>('/financial-health/score');
    return FinancialHealthDto.fromJson(response.data!);
  }
}

final financialHealthApiProvider = Provider<FinancialHealthApi>((ref) {
  return FinancialHealthApi(ref.watch(dioProvider));
});

final financialHealthProvider =
    FutureProvider.autoDispose<FinancialHealthDto>((ref) {
  return ref.watch(financialHealthApiProvider).score();
});
