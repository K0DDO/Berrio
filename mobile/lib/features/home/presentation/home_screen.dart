import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/refresh.dart';
import '../../../shared/widgets/journey_state_panel.dart';
import '../../auth/presentation/auth_controller.dart';
import '../data/dashboard_api.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final async = ref.watch(dashboardProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Berrio',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: scheme.primary,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            Text(
              user == null ? 'Your money, explained' : user.displayName,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          IconButton(
            onPressed: () => refreshMoneySurfaces(ref),
            icon: const Icon(Icons.refresh),
          ),
          IconButton(
            onPressed: () => context.go('/more/settings'),
            icon: const Icon(Icons.settings_outlined),
          ),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => refreshMoneySurfaces(ref),
        ),
        data: (dash) => RefreshIndicator(
          onRefresh: () async => refreshMoneySurfaces(ref),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              _ScoreCard(score: dash.score),
              const SizedBox(height: 12),
              _SpendCard(
                current: dash.currentSpend,
                previous: dash.previousSpend,
                changePct: dash.changePct,
                limit: dash.budgetLimit,
              ),
              if (dash.categoryTrends.isNotEmpty) ...[
                const SizedBox(height: 12),
                _TrendsCard(trends: dash.categoryTrends),
              ],
              if (dash.goals.isNotEmpty) ...[
                const SizedBox(height: 12),
                _GoalsCard(goals: dash.goals),
              ],
              if (dash.aiTitle != null) ...[
                const SizedBox(height: 12),
                _AiCard(title: dash.aiTitle!, body: dash.aiBody ?? ''),
              ] else ...[
                const SizedBox(height: 12),
                const _AiCard(
                  title: 'Начните со скана чека',
                  body:
                      'Отсканируйте QR — появится первый разбор трат и рекомендации.',
                ),
              ],
              if (dash.notifications.isNotEmpty) ...[
                const SizedBox(height: 12),
                _NotesCard(notes: dash.notifications),
              ],
              const SizedBox(height: 16),
              FilledButton.tonalIcon(
                onPressed: () => context.go('/scan'),
                icon: const Icon(Icons.qr_code_scanner),
                label: const Text('Scan a receipt'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScoreCard extends StatelessWidget {
  const _ScoreCard({required this.score});

  final int score;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return _CardShell(
      child: Row(
        children: [
          SizedBox(
            width: 72,
            height: 72,
            child: Stack(
              alignment: Alignment.center,
              children: [
                CircularProgressIndicator(
                  value: score / 100,
                  strokeWidth: 7,
                  backgroundColor: scheme.primary.withValues(alpha: 0.12),
                ),
                Text(
                  '$score',
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Financial Health',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Berrio Score 0–100 — how steady your money feels this month.',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: scheme.onSurface.withValues(alpha: 0.65),
                      ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _SpendCard extends StatelessWidget {
  const _SpendCard({
    required this.current,
    required this.previous,
    required this.changePct,
    required this.limit,
  });

  final String current;
  final String previous;
  final double? changePct;
  final String? limit;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final up = (changePct ?? 0) > 0;
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Monthly spending',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          Text(
            '$current RUB',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          if (limit != null)
            Text('Budget limit: $limit RUB', style: Theme.of(context).textTheme.bodySmall),
          Text(
            changePct == null
                ? 'No prior month to compare'
                : '${up ? '▲' : '▼'} ${changePct!.abs().toStringAsFixed(1)}% vs last month ($previous)',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: up ? scheme.error : scheme.primary,
                ),
          ),
        ],
      ),
    );
  }
}

class _TrendsCard extends StatelessWidget {
  const _TrendsCard({required this.trends});

  final List<CategoryTrendDto> trends;

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Category trends',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          ...trends.take(5).map((t) {
            final icon = switch (t.direction) {
              'up' => Icons.trending_up,
              'down' => Icons.trending_down,
              _ => Icons.trending_flat,
            };
            final label = t.changePct == null
                ? t.direction
                : '${t.changePct!.abs().toStringAsFixed(0)}%';
            return ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: Icon(icon, size: 20),
              title: Text(t.name),
              trailing: Text(label),
            );
          }),
        ],
      ),
    );
  }
}

class _GoalsCard extends StatelessWidget {
  const _GoalsCard({required this.goals});

  final List<DashboardGoalDto> goals;

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Goals',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          ...goals.map(
            (g) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(g.name),
                  const SizedBox(height: 4),
                  LinearProgressIndicator(value: (g.progressPct / 100).clamp(0, 1)),
                  const SizedBox(height: 2),
                  Text(
                    '${g.progressPct.toStringAsFixed(0)}% · ${g.currentAmount}/${g.targetAmount}',
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AiCard extends StatelessWidget {
  const _AiCard({required this.title, required this.body});

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return _CardShell(
      color: scheme.primary.withValues(alpha: 0.06),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.auto_awesome, color: scheme.primary, size: 18),
              const SizedBox(width: 8),
              Text(
                'AI advice',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(title, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 4),
          Text(body, style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _NotesCard extends StatelessWidget {
  const _NotesCard({required this.notes});

  final List<DashboardNoteDto> notes;

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Recent alerts',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 4),
          ...notes.map(
            (n) => ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              title: Text(n.title),
              subtitle: Text(n.message, maxLines: 2, overflow: TextOverflow.ellipsis),
              trailing: Text(n.severity, style: Theme.of(context).textTheme.labelSmall),
            ),
          ),
        ],
      ),
    );
  }
}

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child, this.color});

  final Widget child;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color ?? Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: Padding(padding: const EdgeInsets.all(16), child: child),
    );
  }
}
