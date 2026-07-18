import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class GoalDto {
  GoalDto({
    required this.id,
    required this.name,
    required this.targetAmount,
    required this.currentAmount,
    required this.currency,
    required this.status,
    required this.progressPct,
  });

  final String id;
  final String name;
  final String targetAmount;
  final String currentAmount;
  final String currency;
  final String status;
  final double progressPct;

  factory GoalDto.fromJson(Map<String, dynamic> json) {
    return GoalDto(
      id: json['id'] as String,
      name: json['name'] as String,
      targetAmount: json['target_amount'].toString(),
      currentAmount: json['current_amount'].toString(),
      currency: json['currency'] as String? ?? 'RUB',
      status: json['status'] as String,
      progressPct: (json['progress_pct'] as num?)?.toDouble() ?? 0,
    );
  }
}

class GoalsApi {
  GoalsApi(this._dio);

  final Dio _dio;

  Future<List<GoalDto>> list() async {
    final response = await _dio.get<List<dynamic>>('/goals');
    return (response.data ?? [])
        .map((e) => GoalDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<GoalDto> create({
    required String name,
    required String targetAmount,
    String currentAmount = '0',
  }) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/goals',
      data: {
        'name': name,
        'target_amount': targetAmount,
        'current_amount': currentAmount,
      },
    );
    return GoalDto.fromJson(response.data!);
  }

  Future<GoalDto> updateProgress(String id, String currentAmount) async {
    final response = await _dio.post<Map<String, dynamic>>(
      '/goals/$id/progress',
      data: {'current_amount': currentAmount},
    );
    return GoalDto.fromJson(response.data!);
  }
}

final goalsApiProvider = Provider<GoalsApi>((ref) {
  return GoalsApi(ref.watch(dioProvider));
});

final goalsListProvider = FutureProvider.autoDispose<List<GoalDto>>((ref) {
  return ref.watch(goalsApiProvider).list();
});
