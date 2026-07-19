import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/widgets/journey_state_panel.dart';
import '../data/financial_health_api.dart';

class FinancialHealthScreen extends ConsumerWidget {
  const FinancialHealthScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(financialHealthProvider);
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Berrio Score')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(financialHealthProvider),
        ),
        data: (health) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(financialHealthProvider),
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    children: [
                      SizedBox(
                        width: 120,
                        height: 120,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            CircularProgressIndicator(
                              value: (health.score / 100).clamp(0, 1),
                              strokeWidth: 10,
                              backgroundColor: scheme.primary.withValues(alpha: 0.12),
                            ),
                            Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  '${health.score}',
                                  style: Theme.of(context).textTheme.displaySmall?.copyWith(
                                        fontWeight: FontWeight.w700,
                                      ),
                                ),
                                Text(
                                  '/ 100',
                                  style: Theme.of(context).textTheme.bodySmall,
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      Text(
                        'Финансовое здоровье',
                        style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w600,
                            ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Объяснимый скор на основе трат за месяц',
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                              color: scheme.onSurface.withValues(alpha: 0.65),
                            ),
                      ),
                    ],
                  ),
                ),
              ),
              if (health.factors.positive.isNotEmpty) ...[
                const SizedBox(height: 16),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.thumb_up_outlined, color: scheme.primary, size: 20),
                            const SizedBox(width: 8),
                            Text(
                              'Плюсы',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        ...health.factors.positive.map(
                          (f) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            dense: true,
                            leading: Icon(Icons.check_circle_outline, color: scheme.primary),
                            title: Text(f),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (health.factors.negative.isNotEmpty) ...[
                const SizedBox(height: 12),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(Icons.warning_amber_outlined, color: scheme.error, size: 20),
                            const SizedBox(width: 8),
                            Text(
                              'На что обратить внимание',
                              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                                    fontWeight: FontWeight.w600,
                                  ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        ...health.factors.negative.map(
                          (f) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            dense: true,
                            leading: Icon(Icons.info_outline, color: scheme.error),
                            title: Text(f),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
              if (health.factors.positive.isEmpty && health.factors.negative.isEmpty) ...[
                const SizedBox(height: 24),
                JourneyStatePanel.empty(
                  title: 'Мало данных для скора',
                  message: 'Добавьте чеки за месяц — появятся плюсы и минусы.',
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
