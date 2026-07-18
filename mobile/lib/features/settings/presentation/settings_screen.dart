import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';

class NotificationPreferencesDto {
  NotificationPreferencesDto({
    required this.priceChangesEnabled,
    required this.budgetAlertsEnabled,
    required this.goalAlertsEnabled,
    required this.aiInsightsEnabled,
    required this.unusualSpendingEnabled,
  });

  final bool priceChangesEnabled;
  final bool budgetAlertsEnabled;
  final bool goalAlertsEnabled;
  final bool aiInsightsEnabled;
  final bool unusualSpendingEnabled;

  factory NotificationPreferencesDto.fromJson(Map<String, dynamic> json) {
    return NotificationPreferencesDto(
      priceChangesEnabled: json['price_changes_enabled'] as bool? ?? true,
      budgetAlertsEnabled: json['budget_alerts_enabled'] as bool? ?? true,
      goalAlertsEnabled: json['goal_alerts_enabled'] as bool? ?? true,
      aiInsightsEnabled: json['ai_insights_enabled'] as bool? ?? true,
      unusualSpendingEnabled: json['unusual_spending_enabled'] as bool? ?? true,
    );
  }

  NotificationPreferencesDto copyWith({
    bool? priceChangesEnabled,
    bool? budgetAlertsEnabled,
    bool? goalAlertsEnabled,
    bool? aiInsightsEnabled,
    bool? unusualSpendingEnabled,
  }) {
    return NotificationPreferencesDto(
      priceChangesEnabled: priceChangesEnabled ?? this.priceChangesEnabled,
      budgetAlertsEnabled: budgetAlertsEnabled ?? this.budgetAlertsEnabled,
      goalAlertsEnabled: goalAlertsEnabled ?? this.goalAlertsEnabled,
      aiInsightsEnabled: aiInsightsEnabled ?? this.aiInsightsEnabled,
      unusualSpendingEnabled: unusualSpendingEnabled ?? this.unusualSpendingEnabled,
    );
  }
}

class SettingsApi {
  SettingsApi(this._dio);

  final Dio _dio;

  Future<NotificationPreferencesDto> getPrefs() async {
    final response = await _dio.get<Map<String, dynamic>>('/notifications/preferences');
    return NotificationPreferencesDto.fromJson(response.data!);
  }

  Future<NotificationPreferencesDto> patchPrefs(Map<String, bool> body) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/notifications/preferences',
      data: body,
    );
    return NotificationPreferencesDto.fromJson(response.data!);
  }
}

final settingsApiProvider = Provider<SettingsApi>((ref) {
  return SettingsApi(ref.watch(dioProvider));
});

final notificationPrefsProvider =
    FutureProvider.autoDispose<NotificationPreferencesDto>((ref) {
  return ref.watch(settingsApiProvider).getPrefs();
});

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationPrefsProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed: $e')),
        data: (prefs) => ListView(
          children: [
            const ListTile(
              title: Text('Notification preferences'),
              subtitle: Text('Choose which explainable alerts Berrio may send'),
            ),
            SwitchListTile(
              title: const Text('Price changes'),
              value: prefs.priceChangesEnabled,
              onChanged: (v) => _patch(ref, {'price_changes_enabled': v}),
            ),
            SwitchListTile(
              title: const Text('Budget alerts'),
              value: prefs.budgetAlertsEnabled,
              onChanged: (v) => _patch(ref, {'budget_alerts_enabled': v}),
            ),
            SwitchListTile(
              title: const Text('Goal alerts'),
              value: prefs.goalAlertsEnabled,
              onChanged: (v) => _patch(ref, {'goal_alerts_enabled': v}),
            ),
            SwitchListTile(
              title: const Text('AI insights'),
              value: prefs.aiInsightsEnabled,
              onChanged: (v) => _patch(ref, {'ai_insights_enabled': v}),
            ),
            SwitchListTile(
              title: const Text('Unusual spending'),
              value: prefs.unusualSpendingEnabled,
              onChanged: (v) => _patch(ref, {'unusual_spending_enabled': v}),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _patch(WidgetRef ref, Map<String, bool> body) async {
    await ref.read(settingsApiProvider).patchPrefs(body);
    ref.invalidate(notificationPrefsProvider);
  }
}
