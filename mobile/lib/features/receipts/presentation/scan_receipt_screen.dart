import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../shared/refresh.dart';
import '../../../shared/widgets/journey_state_panel.dart';
import '../../sync/sync_providers.dart';
import '../domain/qr_fiscal_parser.dart';

enum ScanPhase { idle, scanning, processing, success, error, offline, permission }

class ScanReceiptScreen extends ConsumerStatefulWidget {
  const ScanReceiptScreen({super.key});

  @override
  ConsumerState<ScanReceiptScreen> createState() => _ScanReceiptScreenState();
}

class _ScanReceiptScreenState extends ConsumerState<ScanReceiptScreen> {
  final _parser = const QrFiscalParser();
  final _controller = MobileScannerController();
  var _phase = ScanPhase.idle;
  String? _message;
  String? _receiptId;
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
      if (status.isGranted) {
        _phase = ScanPhase.scanning;
      } else {
        _phase = ScanPhase.permission;
        _message = 'Camera permission is required to scan fiscal QR codes.';
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _handleRaw(String raw, {required bool syncNow}) async {
    if (_phase == ScanPhase.processing) return;
    final parsed = _parser.parse(raw);
    if (parsed == null) {
      setState(() {
        _phase = ScanPhase.error;
        _message = 'Invalid FNS QR payload. Try again.';
        _handled = false;
      });
      return;
    }

    setState(() {
      _phase = ScanPhase.processing;
      _message = 'Saving locally and talking to Berrio…';
    });

    try {
      final engine = ref.read(syncEngineProvider);
      await engine.enqueueReceiptScan(parsed);
      if (syncNow) {
        final n = await engine.drainPending();
        if (!mounted) return;
        if (n > 0) {
          final locals = await ref.read(localReceiptsDaoProvider).listAll();
          final match = locals.where(
            (r) =>
                r.fn == parsed['fn'] &&
                r.fd == parsed['fd'] &&
                r.fp == parsed['fp'] &&
                r.synced,
          );
          refreshMoneySurfaces(ref);
          setState(() {
            _phase = ScanPhase.success;
            _receiptId = match.isEmpty ? null : match.first.id;
            _message = 'Receipt loaded. Categories assigned — dashboard updated.';
          });
        } else {
          setState(() {
            _phase = ScanPhase.offline;
            _message = 'Queued offline. Will sync when the network is back.';
          });
        }
      } else {
        if (!mounted) return;
        setState(() {
          _phase = ScanPhase.offline;
          _message = 'Saved offline. Will sync when online.';
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = ScanPhase.error;
        _message = e.toString();
        _handled = false;
      });
    }
  }

  void _resetToScan() {
    setState(() {
      _phase = ScanPhase.scanning;
      _message = null;
      _receiptId = null;
      _handled = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
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
            child: switch (_phase) {
              ScanPhase.permission => JourneyStatePanel(
                  icon: Icons.camera_alt_outlined,
                  title: 'Camera needed',
                  message: _message ?? '',
                  actionLabel: 'Open settings',
                  onAction: openAppSettings,
                ),
              ScanPhase.processing => const Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircularProgressIndicator(),
                      SizedBox(height: 16),
                      Text('Processing receipt…'),
                    ],
                  ),
                ),
              ScanPhase.success => JourneyStatePanel(
                  icon: Icons.check_circle_outline,
                  title: 'Success',
                  message: _message ?? 'Receipt loaded',
                  actionLabel: 'Scan another',
                  onAction: _resetToScan,
                ),
              ScanPhase.error => JourneyStatePanel.error(
                  message: _message ?? 'Scan failed',
                  onRetry: _resetToScan,
                ),
              ScanPhase.offline => JourneyStatePanel.offline(
                  onRetry: () async {
                    setState(() => _phase = ScanPhase.processing);
                    final n = await ref.read(syncEngineProvider).drainPending();
                    refreshMoneySurfaces(ref);
                    if (!mounted) return;
                    setState(() {
                      _phase = n > 0 ? ScanPhase.success : ScanPhase.offline;
                      _message = n > 0
                          ? 'Synced $n receipt(s).'
                          : 'Still offline or nothing to sync.';
                    });
                  },
                ),
              _ => MobileScanner(
                  controller: _controller,
                  onDetect: (capture) {
                    if (_handled || _phase != ScanPhase.scanning) return;
                    final raw = capture.barcodes.firstOrNull?.rawValue;
                    if (raw == null) return;
                    _handled = true;
                    _handleRaw(raw, syncNow: true);
                  },
                ),
            },
          ),
          Expanded(
            flex: 2,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: scheme.surface,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Photos are never stored — only FN/FD/FP from QR.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                  if (_message != null &&
                      _phase != ScanPhase.success &&
                      _phase != ScanPhase.error &&
                      _phase != ScanPhase.offline) ...[
                    const SizedBox(height: 8),
                    Text(_message!),
                  ],
                  const Spacer(),
                  if (_phase == ScanPhase.scanning || _phase == ScanPhase.idle) ...[
                    FilledButton.tonalIcon(
                      onPressed: () => _handleRaw(
                        't=20240115T1200&s=250.00&fn=9281000100123456&i=12345&fp=987654321&n=1',
                        syncNow: false,
                      ),
                      icon: const Icon(Icons.cloud_off),
                      label: const Text('Simulate offline scan'),
                    ),
                  ],
                  if (_phase == ScanPhase.success) ...[
                    if (_receiptId != null)
                      FilledButton.icon(
                        onPressed: () => context.push('/receipts/$_receiptId'),
                        icon: const Icon(Icons.receipt_long),
                        label: const Text('View receipt'),
                      ),
                    const SizedBox(height: 8),
                    OutlinedButton.icon(
                      onPressed: () => context.go('/home'),
                      icon: const Icon(Icons.dashboard_outlined),
                      label: const Text('Open dashboard'),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
