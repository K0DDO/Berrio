import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../features/analytics/data/analytics_api.dart';
import '../features/budgets/data/budgets_api.dart';
import '../features/financial_health/data/financial_health_api.dart';
import '../features/goals/data/goals_api.dart';
import '../features/home/data/dashboard_api.dart';
import '../features/notifications/data/notifications_api.dart';
import '../features/receipts/data/receipts_api.dart';
import '../features/receipts/presentation/receipts_history_screen.dart';

/// Invalidate journey surfaces after money-changing actions.
void refreshMoneySurfaces(WidgetRef ref) {
  ref.invalidate(dashboardProvider);
  ref.invalidate(receiptsListProvider);
  ref.invalidate(localReceiptsProvider);
  ref.invalidate(goalsListProvider);
  ref.invalidate(budgetsListProvider);
  ref.invalidate(notificationsListProvider);
  ref.invalidate(analyticsSummaryProvider);
  ref.invalidate(financialHealthProvider);
}
