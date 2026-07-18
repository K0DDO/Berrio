import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class BudgetDto {
  BudgetDto({
    required this.id,
    required this.name,
    required this.limitAmount,
    required this.spentAmount,
    required this.remainingAmount,
    required this.currency,
    required this.usagePct,
    required this.overBudget,
    required this.periodType,
  });

  final String id;
  final String name;
  final String limitAmount;
  final String spentAmount;
  final String remainingAmount;
  final String currency;
  final double usagePct;
  final bool overBudget;
  final String periodType;

  factory BudgetDto.fromJson(Map<String, dynamic> json) {
    return BudgetDto(
      id: json['id'] as String,
      name: json['name'] as String,
      limitAmount: json['limit_amount'].toString(),
      spentAmount: json['spent_amount'].toString(),
      remainingAmount: json['remaining_amount'].toString(),
      currency: json['currency'] as String? ?? 'RUB',
      usagePct: (json['usage_pct'] as num?)?.toDouble() ?? 0,
      overBudget: json['over_budget'] as bool? ?? false,
      periodType: json['period_type'] as String? ?? 'MONTH',
    );
  }
}

class BudgetsApi {
  BudgetsApi(this._dio);

  final Dio _dio;

  Future<List<BudgetDto>> list() async {
    final response = await _dio.get<List<dynamic>>('/budgets');
    return (response.data ?? [])
        .map((e) => BudgetDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<BudgetDto> create({
    required String name,
    required String limitAmount,
    required String periodStart,
    String? periodEnd,
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/budgets',
      data: {
        'name': name,
        'limit_amount': limitAmount,
        'period_type': 'MONTH',
        'period_start': periodStart,
        if (periodEnd != null) 'period_end': periodEnd,
      },
    );
    return BudgetDto.fromJson(response.data!);
  }
}

final budgetsApiProvider = Provider<BudgetsApi>((ref) {
  return BudgetsApi(ref.watch(dioProvider));
});

final budgetsListProvider = FutureProvider.autoDispose<List<BudgetDto>>((ref) {
  return ref.watch(budgetsApiProvider).list();
});
