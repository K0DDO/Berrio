import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../sync/sync_providers.dart';
import '../data/local_receipts_dao.dart';
import '../data/receipts_api.dart';

final localReceiptsProvider =
    FutureProvider.autoDispose<List<LocalReceiptRecord>>((ref) async {
  return ref.watch(localReceiptsDaoProvider).listAll();
});

final remoteReceiptsProvider =
    FutureProvider.autoDispose<List<ReceiptDto>>((ref) async {
  try {
    return await ref.watch(receiptsApiProvider).list();
  } catch (_) {
    return const [];
  }
});

class ReceiptsHistoryScreen extends ConsumerWidget {
  const ReceiptsHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final localAsync = ref.watch(localReceiptsProvider);
    final remoteAsync = ref.watch(remoteReceiptsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Receipts'),
        actions: [
          IconButton(
            onPressed: () async {
              await ref.read(syncEngineProvider).syncWhenOnline();
              ref.invalidate(localReceiptsProvider);
              ref.invalidate(remoteReceiptsProvider);
            },
            icon: const Icon(Icons.sync),
          ),
          IconButton(
            onPressed: () {
              ref.invalidate(localReceiptsProvider);
              ref.invalidate(remoteReceiptsProvider);
            },
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/scan'),
        child: const Icon(Icons.qr_code_scanner),
      ),
      body: localAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Local DB error: $e')),
        data: (local) {
          final remote = remoteAsync.valueOrNull ?? const <ReceiptDto>[];
          if (local.isEmpty && remote.isEmpty) {
            return const Center(child: Text('No receipts yet. Scan a QR.'));
          }

          // Prefer local (includes offline) and supplement with remote-only.
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
                  '${item.fn} / ${item.fd} / ${item.fp}\n'
                  'Status: ${item.status}${item.synced ? '' : ' (offline)'}',
                ),
                isThreeLine: true,
                trailing: Text(item.total ?? ''),
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
        sortAt: DateTime.now(),
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

class ReceiptDetailScreen extends ConsumerWidget {
  const ReceiptDetailScreen({super.key, required this.receiptId});

  final String receiptId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return FutureBuilder<ReceiptDto?>(
      future: ref.read(receiptsApiProvider).list().then(
            (list) {
              for (final r in list) {
                if (r.id == receiptId) return r;
              }
              return null;
            },
          ),
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        final r = snapshot.data;
        if (r == null) {
          return const Scaffold(body: Center(child: Text('Not found')));
        }
        return Scaffold(
          appBar: AppBar(title: Text(r.storeName ?? 'Receipt')),
          body: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Text('Status: ${r.status}'),
              Text('Total: ${r.totalAmount ?? '-'}'),
              Text('FN/FD/FP: ${r.fn} / ${r.fd} / ${r.fp}'),
              const SizedBox(height: 16),
              Text('Items', style: Theme.of(context).textTheme.titleMedium),
              ...r.items.map(
                (i) => ListTile(
                  title: Text('${i['name_raw']}'),
                  trailing: Text('${i['sum']}'),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
