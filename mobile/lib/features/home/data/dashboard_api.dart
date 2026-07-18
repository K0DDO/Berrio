import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class DashboardDto {
  DashboardDto({
    required this.score,
    required this.currentSpend,
    required this.previousSpend,
    required this.changePct,
    required this.budgetLimit,
    required this.categoryTrends,
    required this.goals,
    required this.notifications,
    this.aiTitle,
    this.aiBody,
  });

  final int score;
  final String currentSpend;
  final String previousSpend;
  final double? changePct;
  final String? budgetLimit;
  final List<CategoryTrendDto> categoryTrends;
  final List<DashboardGoalDto> goals;
  final List<DashboardNoteDto> notifications;
  final String? aiTitle;
  final String? aiBody;

  factory DashboardDto.fromJson(Map<String, dynamic> json) {
    final spend = json['spending'] as Map<String, dynamic>;
    final score = json['berrio_score'] as Map<String, dynamic>;
    final ai = json['ai_recommendation'] as Map<String, dynamic>?;
    return DashboardDto(
      score: score['score'] as int,
      currentSpend: spend['current_month'].toString(),
      previousSpend: spend['previous_month'].toString(),
      changePct: (spend['change_pct'] as num?)?.toDouble(),
      budgetLimit: spend['budget_limit']?.toString(),
      categoryTrends: (json['category_trends'] as List<dynamic>? ?? [])
          .map((e) => CategoryTrendDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      goals: (json['active_goals'] as List<dynamic>? ?? [])
          .map((e) => DashboardGoalDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      notifications: (json['recent_notifications'] as List<dynamic>? ?? [])
          .map((e) => DashboardNoteDto.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList(),
      aiTitle: ai?['title'] as String?,
      aiBody: ai?['body'] as String?,
    );
  }
}

class CategoryTrendDto {
  CategoryTrendDto({
    required this.name,
    required this.direction,
    this.changePct,
  });

  final String name;
  final String direction;
  final double? changePct;

  factory CategoryTrendDto.fromJson(Map<String, dynamic> json) {
    return CategoryTrendDto(
      name: json['category_name'] as String,
      direction: json['direction'] as String,
      changePct: (json['change_pct'] as num?)?.toDouble(),
    );
  }
}

class DashboardGoalDto {
  DashboardGoalDto({
    required this.name,
    required this.progressPct,
    required this.currentAmount,
    required this.targetAmount,
  });

  final String name;
  final double progressPct;
  final String currentAmount;
  final String targetAmount;

  factory DashboardGoalDto.fromJson(Map<String, dynamic> json) {
    return DashboardGoalDto(
      name: json['name'] as String,
      progressPct: (json['progress_pct'] as num).toDouble(),
      currentAmount: json['current_amount'].toString(),
      targetAmount: json['target_amount'].toString(),
    );
  }
}

class DashboardNoteDto {
  DashboardNoteDto({
    required this.title,
    required this.message,
    required this.severity,
  });

  final String title;
  final String message;
  final String severity;

  factory DashboardNoteDto.fromJson(Map<String, dynamic> json) {
    return DashboardNoteDto(
      title: json['title'] as String,
      message: json['message'] as String,
      severity: json['severity'] as String? ?? 'INFO',
    );
  }
}

class DashboardApi {
  DashboardApi(this._dio);

  final Dio _dio;

  Future<DashboardDto> fetch() async {
    final response = await _dio.get<Map<String, dynamic>>('/dashboard');
    return DashboardDto.fromJson(response.data!);
  }
}

final dashboardApiProvider = Provider<DashboardApi>((ref) {
  return DashboardApi(ref.watch(dioProvider));
});

final dashboardProvider = FutureProvider.autoDispose<DashboardDto>((ref) {
  return ref.watch(dashboardApiProvider).fetch();
});
