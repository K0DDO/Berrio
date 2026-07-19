import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/network/dio_client.dart';
import '../../auth/data/local_unlock_store.dart';
import '../../auth/presentation/unlock_screen.dart';

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
}

class UserProfileDto {
  UserProfileDto({
    required this.displayName,
    this.monthlyIncome,
    this.monthlyObligations,
    this.monthlySavingsTarget,
    this.ignoreReceiptTimeDefault = false,
  });

  final String displayName;
  final String? monthlyIncome;
  final String? monthlyObligations;
  final String? monthlySavingsTarget;
  final bool ignoreReceiptTimeDefault;

  factory UserProfileDto.fromJson(Map<String, dynamic> json) {
    return UserProfileDto(
      displayName: json['display_name'] as String? ?? '',
      monthlyIncome: json['monthly_income']?.toString(),
      monthlyObligations: json['monthly_obligations']?.toString(),
      monthlySavingsTarget: json['monthly_savings_target']?.toString(),
      ignoreReceiptTimeDefault:
          json['ignore_receipt_time_default'] as bool? ?? false,
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

  Future<UserProfileDto> getProfile() async {
    final response = await _dio.get<Map<String, dynamic>>('/users/me/profile');
    return UserProfileDto.fromJson(response.data!);
  }

  Future<UserProfileDto> patchProfile(Map<String, dynamic> body) async {
    final response = await _dio.patch<Map<String, dynamic>>(
      '/users/me/profile',
      data: body,
    );
    return UserProfileDto.fromJson(response.data!);
  }
}

final settingsApiProvider = Provider<SettingsApi>((ref) {
  return SettingsApi(ref.watch(dioProvider));
});

final notificationPrefsProvider =
    FutureProvider.autoDispose<NotificationPreferencesDto>((ref) {
  return ref.watch(settingsApiProvider).getPrefs();
});

final userProfileProvider = FutureProvider.autoDispose<UserProfileDto>((ref) {
  return ref.watch(settingsApiProvider).getProfile();
});

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(notificationPrefsProvider);
    final profileAsync = ref.watch(userProfileProvider);
    final unlock = ref.watch(unlockConfigProvider) ?? UnlockConfig.disabled;

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          const ListTile(
            title: Text('Финансы для Berrio Score'),
            subtitle: Text('Доход и обязательные платежи — без стыда за еду при низком доходе'),
          ),
          profileAsync.when(
            loading: () => const LinearProgressIndicator(),
            error: (e, _) => ListTile(title: Text('Профиль: $e')),
            data: (profile) => Column(
              children: [
                ListTile(
                  title: const Text('Месячный доход'),
                  subtitle: Text(profile.monthlyIncome ?? 'не указан'),
                  trailing: const Icon(Icons.edit_outlined),
                  onTap: () => _editMoneyField(
                    context,
                    ref,
                    title: 'Месячный доход',
                    field: 'monthly_income',
                    current: profile.monthlyIncome,
                  ),
                ),
                ListTile(
                  title: const Text('Обязательные платежи'),
                  subtitle: Text(profile.monthlyObligations ?? 'не указаны'),
                  trailing: const Icon(Icons.edit_outlined),
                  onTap: () => _editMoneyField(
                    context,
                    ref,
                    title: 'Обязательные платежи',
                    field: 'monthly_obligations',
                    current: profile.monthlyObligations,
                  ),
                ),
                ListTile(
                  title: const Text('Цель накоплений / мес'),
                  subtitle: Text(profile.monthlySavingsTarget ?? 'не указана'),
                  trailing: const Icon(Icons.edit_outlined),
                  onTap: () => _editMoneyField(
                    context,
                    ref,
                    title: 'Цель накоплений',
                    field: 'monthly_savings_target',
                    current: profile.monthlySavingsTarget,
                  ),
                ),
              ],
            ),
          ),
          const Divider(height: 24),
          const ListTile(
            title: Text('Быстрый вход'),
            subtitle: Text(
              'Биометрия или PIN. Пароль аккаунта не сохраняется.',
            ),
          ),
          SwitchListTile(
            title: const Text('Разблокировка приложения'),
            subtitle: Text(
              unlock.enabled
                  ? (unlock.method == UnlockMethod.pin
                      ? 'PIN'
                      : 'Биометрия')
                  : 'Выключено',
            ),
            value: unlock.enabled,
            onChanged: (v) => _toggleUnlock(context, ref, enable: v),
          ),
          const Divider(height: 24),
          async.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(24),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (e, _) => Padding(
              padding: const EdgeInsets.all(16),
              child: Text('Failed: $e'),
            ),
            data: (prefs) => Column(
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
        ],
      ),
    );
  }

  Future<void> _editMoneyField(
    BuildContext context,
    WidgetRef ref, {
    required String title,
    required String field,
    String? current,
  }) async {
    final controller = TextEditingController(text: current ?? '');
    final value = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(suffixText: '₽'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Отмена')),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );
    if (value == null || value.isEmpty) return;
    await ref.read(settingsApiProvider).patchProfile({field: value});
    ref.invalidate(userProfileProvider);
  }

  Future<void> _patch(WidgetRef ref, Map<String, bool> body) async {
    await ref.read(settingsApiProvider).patchPrefs(body);
    ref.invalidate(notificationPrefsProvider);
  }

  Future<void> _toggleUnlock(
    BuildContext context,
    WidgetRef ref, {
    required bool enable,
  }) async {
    final store = ref.read(localUnlockStoreProvider);
    if (!enable) {
      await store.disable();
      ref.read(unlockConfigProvider.notifier).state = UnlockConfig.disabled;
      ref.read(sessionUnlockedProvider.notifier).state = true;
      return;
    }
    await offerQuickUnlockDialog(context, ref);
  }
}
