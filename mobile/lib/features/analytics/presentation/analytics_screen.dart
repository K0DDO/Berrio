import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/widgets/journey_state_panel.dart';
import '../data/analytics_api.dart';

const _periods = <({String value, String label})>[
  (value: 'day', label: 'День'),
  (value: 'week', label: 'Неделя'),
  (value: 'month', label: 'Месяц'),
  (value: 'year', label: 'Год'),
];

class AnalyticsScreen extends ConsumerWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final period = ref.watch(analyticsPeriodProvider);
    final async = ref.watch(analyticsSummaryProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Аналитика')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Wrap(
              spacing: 8,
              children: _periods.map((p) {
                final selected = period == p.value;
                return FilterChip(
                  label: Text(p.label),
                  selected: selected,
                  onSelected: (_) {
                    ref.read(analyticsPeriodProvider.notifier).state = p.value;
                  },
                );
              }).toList(),
            ),
          ),
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error: (e, _) => JourneyStatePanel.error(
                message: '$e',
                onRetry: () => ref.invalidate(analyticsSummaryProvider),
              ),
              data: (summary) => RefreshIndicator(
                onRefresh: () async => ref.invalidate(analyticsSummaryProvider),
                child: ListView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                  children: [
                    Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Расходы',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              '${summary.totalSpend} ₽',
                              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                    fontWeight: FontWeight.w700,
                                  ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              summary.previousChangePct == null
                                  ? 'Нет данных за прошлый период'
                                  : _changeLabel(summary.previousChangePct!),
                              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: (summary.previousChangePct ?? 0) > 0
                                        ? scheme.error
                                        : scheme.primary,
                                  ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              '${summary.receiptCount} чеков'
                              '${summary.avgReceipt != null ? ' · средний ${summary.avgReceipt} ₽' : ''}',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ),
                    if (summary.berrioScore != null) ...[
                      const SizedBox(height: 12),
                      Card(
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: scheme.primary.withValues(alpha: 0.12),
                            child: Text(
                              '${summary.berrioScore}',
                              style: TextStyle(
                                color: scheme.primary,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                          title: const Text('Berrio Score'),
                          subtitle: const Text('Финансовое здоровье за месяц'),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => context.go('/more/health'),
                        ),
                      ),
                    ],
                    if (summary.byCategory.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'По категориям',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                              const SizedBox(height: 12),
                              ...summary.byCategory.map((c) {
                                final pct = (c.share * 100).clamp(0, 100);
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 12),
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(child: Text(c.categoryName)),
                                          Text(
                                            '${c.amount} ₽ · ${pct.toStringAsFixed(0)}%',
                                            style: Theme.of(context).textTheme.bodySmall,
                                          ),
                                        ],
                                      ),
                                      const SizedBox(height: 6),
                                      LinearProgressIndicator(
                                        value: c.share.clamp(0, 1),
                                      ),
                                    ],
                                  ),
                                );
                              }),
                            ],
                          ),
                        ),
                      ),
                    ],
                    if (summary.topMerchants.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Куда уходят деньги',
                                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                      fontWeight: FontWeight.w600,
                                    ),
                              ),
                              const SizedBox(height: 8),
                              ...summary.topMerchants.map(
                                (m) => ListTile(
                                  contentPadding: EdgeInsets.zero,
                                  dense: true,
                                  title: Text(m.storeName),
                                  subtitle: Text('${m.purchaseCount} покупок'),
                                  trailing: Text('${m.amount} ₽'),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                    if (summary.byCategory.isEmpty && summary.topMerchants.isEmpty) ...[
                      const SizedBox(height: 24),
                      JourneyStatePanel.empty(
                        title: 'Пока нет данных',
                        message: 'Отсканируйте чеки — появится разбор трат по периоду.',
                        actionLabel: 'Сканировать',
                        onAction: () => context.go('/scan'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _changeLabel(double pct) {
    final abs = pct.abs().toStringAsFixed(1);
    if (pct > 0) return '▲ $abs% к прошлому периоду';
    if (pct < 0) return '▼ $abs% к прошлому периоду';
    return 'Без изменений к прошлому периоду';
  }
}
