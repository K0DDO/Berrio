import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../shared/widgets/journey_state_panel.dart';
import '../../sync/sync_providers.dart';
import '../data/local_receipts_dao.dart';
import '../data/receipts_api.dart';

final localReceiptsProvider =
    FutureProvider.autoDispose<List<LocalReceiptRecord>>((ref) async {
  return ref.watch(localReceiptsDaoProvider).listAll();
});

class ReceiptsHistoryScreen extends ConsumerWidget {
  const ReceiptsHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final localAsync = ref.watch(localReceiptsProvider);
    final remoteAsync = ref.watch(receiptsListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Receipts'),
        actions: [
          IconButton(
            onPressed: () async {
              await ref.read(syncEngineProvider).syncWhenOnline();
              ref.invalidate(localReceiptsProvider);
              ref.invalidate(receiptsListProvider);
            },
            icon: const Icon(Icons.sync),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/scan'),
        child: const Icon(Icons.qr_code_scanner),
      ),
      body: localAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(localReceiptsProvider),
        ),
        data: (local) {
          final remote = remoteAsync.valueOrNull ?? const <ReceiptDto>[];
          if (local.isEmpty && remote.isEmpty) {
            return JourneyStatePanel.empty(
              title: 'No receipts yet',
              message: 'Scan a fiscal QR in the store — Berrio will do the rest.',
              actionLabel: 'Scan receipt',
              onAction: () => context.go('/scan'),
            );
          }
          final byKey = <String, _HistoryItem>{};
          for (final r in remote) {
            byKey['${r.fn}|${r.fd}|${r.fp}'] = _HistoryItem.fromRemote(r);
          }
          for (final r in local) {
            byKey['${r.fn}|${r.fd}|${r.fp}'] = _HistoryItem.fromLocal(r);
          }
          final items = byKey.values.toList()
            ..sort((a, b) => b.sortAt.compareTo(a.sortAt));

          return ListView.separated(
            itemCount: items.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final item = items[index];
              return ListTile(
                title: Text(item.title),
                subtitle: Text(
                  '${item.status}${item.synced ? '' : ' · offline'}'
                  '${item.total != null ? '\n${item.total} RUB' : ''}',
                ),
                isThreeLine: item.total != null,
                trailing: const Icon(Icons.chevron_right),
                onTap: item.serverId == null
                    ? null
                    : () => context.push('/receipts/${item.serverId}'),
              );
            },
          );
        },
      ),
    );
  }
}

class _HistoryItem {
  _HistoryItem({
    required this.title,
    required this.fn,
    required this.fd,
    required this.fp,
    required this.status,
    required this.synced,
    required this.sortAt,
    this.total,
    this.serverId,
  });

  factory _HistoryItem.fromLocal(LocalReceiptRecord r) => _HistoryItem(
        title: r.storeName ?? (r.synced ? 'Receipt' : 'Queued receipt'),
        fn: r.fn,
        fd: r.fd,
        fp: r.fp,
        status: r.status,
        synced: r.synced,
        sortAt: r.createdAt,
        total: r.totalAmount,
        serverId: r.synced ? r.id : null,
      );

  factory _HistoryItem.fromRemote(ReceiptDto r) => _HistoryItem(
        title: r.storeName ?? 'Receipt',
        fn: r.fn,
        fd: r.fd,
        fp: r.fp,
        status: r.status,
        synced: true,
        sortAt: r.purchasedAt ?? DateTime.now(),
        total: r.totalAmount,
        serverId: r.id,
      );

  final String title;
  final String fn;
  final String fd;
  final String fp;
  final String status;
  final bool synced;
  final DateTime sortAt;
  final String? total;
  final String? serverId;
}

class ReceiptDetailsScreen extends ConsumerWidget {
  const ReceiptDetailsScreen({super.key, required this.receiptId});

  final String receiptId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(receiptDetailProvider(receiptId));
    final scheme = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(title: const Text('Receipt')),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => JourneyStatePanel.error(
          message: '$e',
          onRetry: () => ref.invalidate(receiptDetailProvider(receiptId)),
        ),
        data: (r) {
          final date = r.purchasedAt != null
              ? DateFormat('d MMM yyyy, HH:mm').format(r.purchasedAt!.toLocal())
              : '—';
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
            children: [
              Text(
                r.storeName ?? 'Store',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              Text(date, style: Theme.of(context).textTheme.bodyMedium),
              const SizedBox(height: 4),
              Text(
                '${r.totalAmount ?? '—'} RUB',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      color: scheme.primary,
                      fontWeight: FontWeight.w700,
                    ),
              ),
              const SizedBox(height: 4),
              Text(
                'Status: ${r.status}',
                style: Theme.of(context).textTheme.labelMedium,
              ),
              const SizedBox(height: 20),
              Text(
                'Items',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 8),
              ...r.items.map((i) {
                final priceNote = i.priceChangePct == null
                    ? null
                    : '${i.priceChangePct! > 0 ? '+' : ''}${i.priceChangePct!.toStringAsFixed(0)}%'
                        '${i.previousPrice != null ? ' vs ${i.previousPrice}' : ''}';
                return Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  elevation: 0,
                  color: Colors.white,
                  child: ListTile(
                    title: Text(i.nameRaw),
                    subtitle: Text(
                      [
                        if (i.categoryName != null) i.categoryName!,
                        if (priceNote != null) priceNote,
                      ].join(' · '),
                    ),
                    trailing: Text(i.sum),
                  ),
                );
              }),
            ],
          );
        },
      ),
    );
  }
}
