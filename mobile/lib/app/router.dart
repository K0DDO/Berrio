import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/ai/presentation/ai_screen.dart';
import '../features/analytics/presentation/analytics_screen.dart';
import '../features/auth/data/local_unlock_store.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/auth/presentation/register_screen.dart';
import '../features/auth/presentation/splash_screen.dart';
import '../features/auth/presentation/unlock_screen.dart';
import '../features/banks/presentation/banks_screen.dart';
import '../features/budgets/presentation/budgets_screen.dart';
import '../features/family/presentation/family_screen.dart';
import '../features/financial_health/presentation/financial_health_screen.dart';
import '../features/goals/presentation/goals_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/notifications/presentation/notifications_screen.dart';
import '../features/onboarding/presentation/welcome_screen.dart';
import '../features/receipts/presentation/receipt_confirm_screen.dart';
import '../features/receipts/presentation/receipts_history_screen.dart';
import '../features/receipts/presentation/scan_receipt_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../shared/widgets/app_shell.dart';

/// null = still loading from secure storage.
final onboardingSeenProvider = StateProvider<bool?>((ref) => null);

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authControllerProvider);
  final onboardingSeen = ref.watch(onboardingSeenProvider);
  final unlockConfig = ref.watch(unlockConfigProvider);
  final sessionUnlocked = ref.watch(sessionUnlockedProvider);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: _RouterListenable(ref),
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final authGate = loc == '/login' ||
          loc == '/register' ||
          loc == '/splash' ||
          loc == '/welcome';
      final onUnlock = loc == '/unlock';

      if (auth.status == AuthStatus.unknown ||
          onboardingSeen == null ||
          unlockConfig == null) {
        return loc == '/splash' ? null : '/splash';
      }

      if (auth.status == AuthStatus.unauthenticated) {
        if (!onboardingSeen) {
          return loc == '/welcome' ? null : '/welcome';
        }
        if (loc == '/welcome' || loc == '/splash' || onUnlock) return '/login';
        return authGate && loc != '/splash' ? null : '/login';
      }

      // Authenticated but local unlock required for this session.
      final needsUnlock = unlockConfig.enabled && !sessionUnlocked;
      if (needsUnlock) {
        return onUnlock ? null : '/unlock';
      }
      if (onUnlock) return '/home';

      // Authenticated → dashboard (first launch after register included).
      if (authGate) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/welcome', builder: (context, state) => const WelcomeScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/register', builder: (context, state) => const RegisterScreen()),
      GoRoute(path: '/unlock', builder: (context, state) => const UnlockScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) {
          return AppShell(navigationShell: navigationShell);
        },
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/home', builder: (context, state) => const HomeScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/scan', builder: (context, state) => const ScanReceiptScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/analytics',
                builder: (context, state) => const AnalyticsScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(path: '/ai', builder: (context, state) => const AiScreen()),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/more',
                builder: (context, state) => const _MoreHubScreen(),
                routes: [
                  GoRoute(path: 'goals', builder: (context, state) => const GoalsScreen()),
                  GoRoute(
                    path: 'notifications',
                    builder: (context, state) => const NotificationsScreen(),
                  ),
                  GoRoute(
                    path: 'health',
                    builder: (context, state) => const FinancialHealthScreen(),
                  ),
                  GoRoute(
                    path: 'budgets',
                    builder: (context, state) => const BudgetsScreen(),
                  ),
                  GoRoute(
                    path: 'family',
                    builder: (context, state) => const FamilyScreen(),
                  ),
                  GoRoute(
                    path: 'banks',
                    builder: (context, state) => const BanksScreen(),
                  ),
                  GoRoute(
                    path: 'receipts',
                    builder: (context, state) => const ReceiptsHistoryScreen(),
                  ),
                  GoRoute(
                    path: 'settings',
                    builder: (context, state) => const SettingsScreen(),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/receipts',
        builder: (context, state) => const ReceiptsHistoryScreen(),
        routes: [
          GoRoute(
            path: ':id/confirm',
            builder: (context, state) => ReceiptConfirmScreen(
              receiptId: state.pathParameters['id']!,
            ),
          ),
          GoRoute(
            path: ':id',
            builder: (context, state) => ReceiptDetailsScreen(
              receiptId: state.pathParameters['id']!,
            ),
          ),
        ],
      ),
    ],
  );
});

class _RouterListenable extends ChangeNotifier {
  _RouterListenable(this._ref) {
    _ref.listen(authControllerProvider, (_, __) => notifyListeners());
    _ref.listen(onboardingSeenProvider, (_, __) => notifyListeners());
    _ref.listen(unlockConfigProvider, (_, __) => notifyListeners());
    _ref.listen(sessionUnlockedProvider, (_, __) => notifyListeners());
  }

  final Ref _ref;
}

class _MoreHubScreen extends ConsumerWidget {
  const _MoreHubScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final items = <({String title, String path, IconData icon})>[
      (title: 'Цели', path: '/more/goals', icon: Icons.flag_outlined),
      (
        title: 'Уведомления',
        path: '/more/notifications',
        icon: Icons.notifications_outlined,
      ),
      (
        title: 'Berrio Score',
        path: '/more/health',
        icon: Icons.favorite_outline,
      ),
      (title: 'Бюджеты', path: '/more/budgets', icon: Icons.pie_chart_outline),
      (title: 'Семья', path: '/more/family', icon: Icons.family_restroom),
      (
        title: 'Банки',
        path: '/more/banks',
        icon: Icons.account_balance_outlined,
      ),
      (title: 'Чеки', path: '/receipts', icon: Icons.receipt_long),
      (title: 'Настройки', path: '/more/settings', icon: Icons.settings_outlined),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('Ещё'),
        actions: [
          IconButton(
            tooltip: 'Выйти',
            onPressed: () async {
              await ref.read(authControllerProvider.notifier).logout();
              ref.read(sessionUnlockedProvider.notifier).state = false;
            },
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: ListView(
        children: [
          if (user != null)
            ListTile(
              title: Text(user.displayName),
              subtitle: Text(user.email),
            ),
          const Divider(height: 1),
          ...items.map(
            (item) => ListTile(
              leading: Icon(item.icon),
              title: Text(item.title),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => context.go(item.path),
            ),
          ),
        ],
      ),
    );
  }
}
