import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../features/ai/presentation/ai_screen.dart';
import '../features/analytics/presentation/analytics_screen.dart';
import '../features/auth/presentation/auth_controller.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/auth/presentation/register_screen.dart';
import '../features/auth/presentation/splash_screen.dart';
import '../features/budgets/presentation/budgets_screen.dart';
import '../features/family/presentation/family_screen.dart';
import '../features/financial_health/presentation/financial_health_screen.dart';
import '../features/goals/presentation/goals_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/notifications/presentation/notifications_screen.dart';
import '../features/receipts/presentation/receipts_history_screen.dart';
import '../features/receipts/presentation/scan_receipt_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import '../shared/widgets/app_shell.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authControllerProvider);

  return GoRouter(
    initialLocation: '/splash',
    refreshListenable: _AuthListenable(ref),
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final loggingIn = loc == '/login' || loc == '/register' || loc == '/splash';

      if (auth.status == AuthStatus.unknown) {
        return loc == '/splash' ? null : '/splash';
      }
      if (auth.status == AuthStatus.unauthenticated) {
        return loggingIn && loc != '/splash' ? null : '/login';
      }
      if (loggingIn || loc == '/splash') {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(path: '/splash', builder: (context, state) => const SplashScreen()),
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/register', builder: (context, state) => const RegisterScreen()),
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
            path: ':id',
            builder: (context, state) => ReceiptDetailScreen(
              receiptId: state.pathParameters['id']!,
            ),
          ),
        ],
      ),
    ],
  );
});

class _AuthListenable extends ChangeNotifier {
  _AuthListenable(this._ref) {
    _ref.listen(authControllerProvider, (_, __) => notifyListeners());
  }

  final Ref _ref;
}

class _MoreHubScreen extends ConsumerWidget {
  const _MoreHubScreen();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final items = <({String title, String path, IconData icon})>[
      (title: 'Goals', path: '/more/goals', icon: Icons.flag_outlined),
      (
        title: 'Notifications',
        path: '/more/notifications',
        icon: Icons.notifications_outlined,
      ),
      (
        title: 'Berrio Score',
        path: '/more/health',
        icon: Icons.favorite_outline,
      ),
      (title: 'Budgets', path: '/more/budgets', icon: Icons.pie_chart_outline),
      (title: 'Family', path: '/more/family', icon: Icons.family_restroom),
      (title: 'Receipts', path: '/receipts', icon: Icons.receipt_long),
      (title: 'Settings', path: '/more/settings', icon: Icons.settings_outlined),
    ];

    return Scaffold(
      appBar: AppBar(
        title: const Text('More'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            onPressed: () => ref.read(authControllerProvider.notifier).logout(),
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
