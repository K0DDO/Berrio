import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class CategorySpendDto {
  CategorySpendDto({
    required this.categoryName,
    required this.amount,
    required this.share,
    this.categoryId,
  });

  final String? categoryId;
  final String categoryName;
  final String amount;
  final double share;

  factory CategorySpendDto.fromJson(Map<String, dynamic> json) {
    return CategorySpendDto(
      categoryId: json['category_id']?.toString(),
      categoryName: json['category_name'] as String? ?? 'Без категории',
      amount: json['amount']?.toString() ?? '0',
      share: (json['share'] as num?)?.toDouble() ?? 0,
    );
  }
}

class MerchantSpendDto {
  MerchantSpendDto({
    required this.storeName,
    required this.purchaseCount,
    required this.amount,
  });

  final String storeName;
  final int purchaseCount;
  final String amount;

  factory MerchantSpendDto.fromJson(Map<String, dynamic> json) {
    return MerchantSpendDto(
      storeName: json['store_name'] as String? ?? '—',
      purchaseCount: json['purchase_count'] as int? ?? 0,
      amount: json['amount']?.toString() ?? '0',
    );
  }
}

class ScoreFactorsDto {
  ScoreFactorsDto({
    required this.positive,
    required this.negative,
  });

  final List<String> positive;
  final List<String> negative;

  factory ScoreFactorsDto.fromJson(Map<String, dynamic>? json) {
    if (json == null) {
      return ScoreFactorsDto(positive: const [], negative: const []);
    }
    return ScoreFactorsDto(
      positive: (json['positive'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
      negative: (json['negative'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
    );
  }
}

class AnalyticsSummaryDto {
  AnalyticsSummaryDto({
    required this.period,
    required this.totalSpend,
    required this.receiptCount,
    required this.byCategory,
    required this.topMerchants,
    this.avgReceipt,
    this.previousTotalSpend,
    this.previousChangePct,
    this.berrioScore,
    this.scoreFactors,
  });

  final String period;
  final String totalSpend;
  final int receiptCount;
  final String? avgReceipt;
  final String? previousTotalSpend;
  final double? previousChangePct;
  final List<CategorySpendDto> byCategory;
  final List<MerchantSpendDto> topMerchants;
  final int? berrioScore;
  final ScoreFactorsDto? scoreFactors;

  factory AnalyticsSummaryDto.fromJson(Map<String, dynamic> json) {
    final factorsRaw = json['score_factors'];
    return AnalyticsSummaryDto(
      period: json['period'] as String? ?? 'month',
      totalSpend: json['total_spend']?.toString() ?? '0',
      receiptCount: json['receipt_count'] as int? ?? 0,
      avgReceipt: json['avg_receipt']?.toString(),
      previousTotalSpend: json['previous_total_spend']?.toString(),
      previousChangePct: (json['previous_change_pct'] as num?)?.toDouble(),
      byCategory: (json['by_category'] as List<dynamic>? ?? [])
          .map((e) => CategorySpendDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      topMerchants: (json['top_merchants'] as List<dynamic>? ?? [])
          .map((e) => MerchantSpendDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      berrioScore: json['berrio_score'] as int?,
      scoreFactors: factorsRaw is Map
          ? ScoreFactorsDto.fromJson(Map<String, dynamic>.from(factorsRaw))
          : null,
    );
  }
}

class AnalyticsApi {
  AnalyticsApi(this._dio);

  final Dio _dio;

  Future<AnalyticsSummaryDto> summary({required String period}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/analytics/summary',
      queryParameters: {'period': period},
    );
    return AnalyticsSummaryDto.fromJson(response.data!);
  }

  Future<List<double>> timeseries({required String period}) async {
    final response = await _dio.get<Map<String, dynamic>>(
      '/analytics/timeseries',
      queryParameters: {'period': period},
    );
    final points = response.data?['points'] as List<dynamic>? ?? [];
    return points
        .map((e) => double.tryParse('${(e as Map)['amount']}') ?? 0.0)
        .toList();
  }
}

final analyticsApiProvider = Provider<AnalyticsApi>((ref) {
  return AnalyticsApi(ref.watch(dioProvider));
});

/// Selected analytics period: day | week | month | year
final analyticsPeriodProvider = StateProvider<String>((ref) => 'month');

final analyticsSummaryProvider =
    FutureProvider.autoDispose<AnalyticsSummaryDto>((ref) {
  final period = ref.watch(analyticsPeriodProvider);
  return ref.watch(analyticsApiProvider).summary(period: period);
});

final analyticsTimeseriesProvider =
    FutureProvider.autoDispose<List<double>>((ref) {
  final period = ref.watch(analyticsPeriodProvider);
  return ref.watch(analyticsApiProvider).timeseries(period: period);
});