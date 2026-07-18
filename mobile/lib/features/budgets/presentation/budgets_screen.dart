import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/refresh.dart';
import '../../../shared/widgets/journey_state_panel.dart';
import '../data/budgets_api.dart';

class BudgetsScreen extends ConsumerWidget {
  const BudgetsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(budgetsListProvider);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Budgets')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        child: const Icon(Icons.add),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(budgetsListProvider),
        ),
        data: (budgets) {
          if (budgets.isEmpty) {
            return JourneyStatePanel.empty(
              title: 'No budgets yet',
              message: 'Set a monthly limit — overspend alerts appear on the dashboard.',
              actionLabel: 'Add budget',
              onAction: () => _showCreateDialog(context, ref),
            );
          }
          return ListView.separated(
            itemCount: budgets.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final b = budgets[index];
              return ListTile(
                title: Text(b.name),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 4),
                    Text(
                      'Spent ${b.spentAmount} / ${b.limitAmount} ${b.currency}',
                      style: TextStyle(
                        color: b.overBudget ? scheme.error : null,
                      ),
                    ),
                    const SizedBox(height: 6),
                    LinearProgressIndicator(
                      value: (b.usagePct / 100).clamp(0, 1),
                      color: b.overBudget ? scheme.error : null,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${b.usagePct.toStringAsFixed(0)}% · ${b.periodType}'
                      '${b.overBudget ? ' · OVER' : ''}',
                    ),
                  ],
                ),
                isThreeLine: true,
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
    final nameCtrl = TextEditingController(text: 'Monthly spend');
    final limitCtrl = TextEditingController(text: '30000');
    final now = DateTime.now();
    final start = DateTime(now.year, now.month, 1);
    final end = DateTime(now.year, now.month + 1, 0);
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New budget'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
            TextField(
              controller: limitCtrl,
              decoration: const InputDecoration(labelText: 'Limit amount'),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Create')),
        ],
      ),
    );
    if (ok != true) return;
    String fmt(DateTime d) =>
        '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
    await ref.read(budgetsApiProvider).create(
          name: nameCtrl.text.trim(),
          limitAmount: limitCtrl.text.trim(),
          periodStart: fmt(start),
          periodEnd: fmt(end),
        );
    refreshMoneySurfaces(ref);
  }
}
