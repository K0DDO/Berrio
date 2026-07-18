import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../sync/sync_providers.dart';
import '../domain/qr_fiscal_parser.dart';

class ScanReceiptScreen extends ConsumerStatefulWidget {
  const ScanReceiptScreen({super.key});

  @override
  ConsumerState<ScanReceiptScreen> createState() => _ScanReceiptScreenState();
}

class _ScanReceiptScreenState extends ConsumerState<ScanReceiptScreen> {
  final _manualController = TextEditingController();
  final _parser = const QrFiscalParser();
  String? _message;
  var _busy = false;

  @override
  void dispose() {
    _manualController.dispose();
    super.dispose();
  }

  Future<void> _enqueueFromRaw(String raw, {required bool syncNow}) async {
    final parsed = _parser.parse(raw);
    if (parsed == null) {
      setState(() => _message = 'Invalid FNS QR payload');
      return;
    }
    setState(() {
      _busy = true;
      _message = null;
    });
    final engine = ref.read(syncEngineProvider);
    await engine.enqueueReceiptScan(parsed);
    var synced = 0;
    if (syncNow) {
      synced = await engine.drainPending();
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _message = syncNow
          ? 'Queued and synced ($synced). Photos are never stored.'
          : 'Saved offline to sync_queue. Will sync when online.';
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan receipt')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Offline-first',
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
              'Paste FNS QR text or use demo. Camera scanner hooks in when Flutter SDK is set up (mobile_scanner).',
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _manualController,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'QR payload',
                hintText: 't=...&s=250.00&fn=...&i=...&fp=...&n=1',
                border: OutlineInputBorder(),
              ),
            ),
            if (_message != null) ...[
              const SizedBox(height: 12),
              Text(_message!),
            ],
            const Spacer(),
            FilledButton.icon(
              onPressed: _busy
                  ? null
                  : () => _enqueueFromRaw(
                        't=20240115T1200&s=250.00&fn=9281000100123456&i=12345&fp=987654321&n=1',
                        syncNow: false,
                      ),
              icon: const Icon(Icons.cloud_off),
              label: const Text('Simulate offline scan'),
            ),
            const SizedBox(height: 8),
            FilledButton.tonalIcon(
              onPressed: _busy
                  ? null
                  : () async {
                      final raw = _manualController.text.trim().isEmpty
                          ? 't=20240115T1200&s=199.90&fn=9281999999999999&i=555&fp=111&n=1'
                          : _manualController.text.trim();
                      await _enqueueFromRaw(raw, syncNow: true);
                    },
              icon: const Icon(Icons.cloud_upload),
              label: const Text('Queue + sync now'),
            ),
            const SizedBox(height: 8),
            OutlinedButton.icon(
              onPressed: _busy
                  ? null
                  : () async {
                      setState(() => _busy = true);
                      final n = await ref.read(syncEngineProvider).drainPending();
                      if (!mounted) return;
                      setState(() {
                        _busy = false;
                        _message = 'Drained sync queue: $n job(s)';
                      });
                    },
              icon: const Icon(Icons.sync),
              label: const Text('Drain pending sync'),
            ),
          ],
        ),
      ),
    );
  }
}
