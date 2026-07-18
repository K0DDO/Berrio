import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../sync/sync_providers.dart';
import '../domain/qr_fiscal_parser.dart';

class ScanReceiptScreen extends ConsumerStatefulWidget {
  const ScanReceiptScreen({super.key});

  @override
  ConsumerState<ScanReceiptScreen> createState() => _ScanReceiptScreenState();
}

class _ScanReceiptScreenState extends ConsumerState<ScanReceiptScreen> {
  final _parser = const QrFiscalParser();
  final _controller = MobileScannerController();
  String? _message;
  var _busy = false;
  var _cameraReady = false;
  var _handled = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final status = await Permission.camera.request();
    if (!mounted) return;
    setState(() {
      _cameraReady = status.isGranted;
      if (!status.isGranted) {
        _message = 'Camera permission required to scan QR receipts';
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleRaw(String raw, {required bool syncNow}) async {
    if (_busy) return;
    final parsed = _parser.parse(raw);
    if (parsed == null) {
      setState(() => _message = 'Invalid FNS QR payload');
      return;
    }
    setState(() {
      _busy = true;
      _message = 'Queued locally…';
    });
    final engine = ref.read(syncEngineProvider);
    await engine.enqueueReceiptScan(parsed);
    var synced = 0;
    if (syncNow) {
      synced = await engine.drainPending();
    } else {
      await engine.syncWhenOnline();
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _message = syncNow
          ? 'Synced $synced receipt(s). Status: processing on server.'
          : 'Saved offline. Will sync when online.';
      _handled = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan receipt'),
        actions: [
          IconButton(
            tooltip: 'History',
            onPressed: () => context.push('/receipts'),
            icon: const Icon(Icons.history),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            flex: 3,
            child: _cameraReady
                ? MobileScanner(
                    controller: _controller,
                    onDetect: (capture) {
                      if (_handled || _busy) return;
                      final raw = capture.barcodes.firstOrNull?.rawValue;
                      if (raw == null) return;
                      _handled = true;
                      _handleRaw(raw, syncNow: true);
                    },
                  )
                : const Center(child: Text('Waiting for camera permission…')),
          ),
          Expanded(
            flex: 2,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Photos are never stored — only FN/FD/FP from QR.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (_message != null) ...[
                    const SizedBox(height: 8),
                    Text(_message!),
                  ],
                  const Spacer(),
                  FilledButton.icon(
                    onPressed: _busy
                        ? null
                        : () => _handleRaw(
                              't=20240115T1200&s=250.00&fn=9281000100123456&i=12345&fp=987654321&n=1',
                              syncNow: false,
                            ),
                    icon: const Icon(Icons.cloud_off),
                    label: const Text('Simulate offline scan'),
                  ),
                  const SizedBox(height: 8),
                  OutlinedButton.icon(
                    onPressed: _busy
                        ? null
                        : () async {
                            setState(() => _busy = true);
                            final n =
                                await ref.read(syncEngineProvider).drainPending();
                            if (!mounted) return;
                            setState(() {
                              _busy = false;
                              _message = 'Drained sync queue: $n';
                            });
                          },
                    icon: const Icon(Icons.sync),
                    label: const Text('Drain pending sync'),
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
