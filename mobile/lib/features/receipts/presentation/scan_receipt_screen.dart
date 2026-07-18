import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../sync/sync_providers.dart';

class ScanReceiptScreen extends ConsumerWidget {
  const ScanReceiptScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan receipt')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Offline-ready',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    color: Theme.of(context).colorScheme.primary,
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Scan receipt',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            const Text(
              'Camera + FNS arrive in Stage 3. For now, tapping queues a local sync job.',
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: () async {
                await ref.read(syncEngineProvider).enqueueReceiptScan({
                  'fn': 'demo',
                  'fd': '1',
                  'fp': '1',
                  'offline': true,
                });
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Queued RECEIPT_SCAN → sync_queue (local)'),
                    ),
                  );
                }
              },
              icon: const Icon(Icons.qr_code_2),
              label: const Text('Simulate offline scan'),
            ),
          ],
        ),
      ),
    );
  }
}
