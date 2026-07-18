import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../shared/refresh.dart';
import '../../../shared/widgets/journey_state_panel.dart';
import '../data/goals_api.dart';

class GoalsScreen extends ConsumerWidget {
  const GoalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(goalsListProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Goals')),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _showCreateDialog(context, ref),
        child: const Icon(Icons.add),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(goalsListProvider),
        ),
        data: (goals) {
          if (goals.isEmpty) {
            return JourneyStatePanel.empty(
              title: 'No goals yet',
              message: 'Add a savings target — progress will show on the dashboard.',
              actionLabel: 'Add goal',
              onAction: () => _showCreateDialog(context, ref),
            );
          }
          return ListView.separated(
            itemCount: goals.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final g = goals[index];
              return ListTile(
                title: Text(g.name),
                subtitle: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 4),
                    Text('${g.currentAmount} / ${g.targetAmount} ${g.currency}'),
                    const SizedBox(height: 6),
                    LinearProgressIndicator(value: (g.progressPct / 100).clamp(0, 1)),
                    const SizedBox(height: 4),
                    Text('${g.progressPct.toStringAsFixed(0)}% · ${g.status}'),
                  ],
                ),
                isThreeLine: true,
                onTap: () => _showProgressDialog(context, ref, g),
              );
            },
          );
        },
      ),
    );
  }

  Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
    final nameCtrl = TextEditingController();
    final targetCtrl = TextEditingController(text: '10000');
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New goal'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: nameCtrl, decoration: const InputDecoration(labelText: 'Name')),
            TextField(
              controller: targetCtrl,
              decoration: const InputDecoration(labelText: 'Target amount'),
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
    await ref.read(goalsApiProvider).create(
          name: nameCtrl.text.trim(),
          targetAmount: targetCtrl.text.trim(),
        );
    refreshMoneySurfaces(ref);
  }

  Future<void> _showProgressDialog(
    BuildContext context,
    WidgetRef ref,
    GoalDto goal,
  ) async {
    final ctrl = TextEditingController(text: goal.currentAmount);
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(goal.name),
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(labelText: 'Current amount'),
          keyboardType: TextInputType.number,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true) return;
    await ref.read(goalsApiProvider).updateProgress(goal.id, ctrl.text.trim());
    refreshMoneySurfaces(ref);
  }
}
