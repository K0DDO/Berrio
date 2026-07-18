import 'dart:async';

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

class _ScanReceiptScreenState extends ConsumerState<ScanReceiptScreen>
    with WidgetsBindingObserver {
  final _parser = const QrFiscalParser();
  MobileScannerController? _controller;
  var _phase = ScanPhase.idle;
  String? _message;
  String? _receiptId;
  var _handled = false;
  var _starting = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _initCamera());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final controller = _controller;
    if (controller == null || !controller.value.hasCameraPermission) return;
    if (_phase != ScanPhase.scanning) return;

    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.hidden ||
        state == AppLifecycleState.detached) {
      unawaited(controller.stop());
    } else if (state == AppLifecycleState.resumed) {
      unawaited(_safeStart());
    }
  }

  Future<void> _safeStart() async {
    final controller = _controller;
    if (controller == null || _starting || !mounted) return;
    if (_phase != ScanPhase.scanning) return;
    _starting = true;
    try {
      await controller.start();
    } on MobileScannerException catch (e) {
      if (!mounted) return;
      // Already running / transient — ignore; real failures show via errorBuilder.
      if (e.errorCode == MobileScannerErrorCode.controllerAlreadyInitialized ||
          e.errorCode == MobileScannerErrorCode.controllerInitializing) {
        return;
      }
      setState(() {
        _phase = ScanPhase.error;
        _message = e.errorDetails?.message ?? e.errorCode.name;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _phase = ScanPhase.error;
        _message = e.toString();
      });
    } finally {
      _starting = false;
    }
  }

  Future<void> _initCamera() async {
    var status = await Permission.camera.status;
    if (!status.isGranted) {
      status = await Permission.camera.request();
    }
    if (!mounted) return;

    if (!status.isGranted) {
      setState(() {
        _phase = ScanPhase.permission;
        _message = status.isPermanentlyDenied
            ? 'Camera access is blocked. Enable it in system settings.'
            : 'Camera permission is required to scan fiscal QR codes.';
      });
      return;
    }

    await _disposeController();
    final controller = MobileScannerController(
      autoStart: false,
      facing: CameraFacing.back,
      detectionSpeed: DetectionSpeed.normal,
      formats: const [BarcodeFormat.qrCode],
    );
    if (!mounted) {
      await controller.dispose();
      return;
    }

    setState(() {
      _controller = controller;
      _phase = ScanPhase.scanning;
      _message = null;
      _handled = false;
    });

    // Let the MobileScanner widget mount before starting CameraX.
    await Future<void>.delayed(const Duration(milliseconds: 250));
    if (!mounted || _controller != controller) return;
    await _safeStart();
  }

  Future<void> _disposeController() async {
    final old = _controller;
    _controller = null;
    if (old == null) return;
    try {
      await old.stop();
    } catch (_) {}
    await old.dispose();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    final c = _controller;
    _controller = null;
    c?.dispose();
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

    try {
      await _controller?.stop();
    } catch (_) {}

    setState(() {
      _phase = ScanPhase.processing;
      _message = 'Saving locally and talking to Berrio…';
    });

    try {
      final engine = ref.read(syncEngineProvider);
      await engine.enqueueReceiptScan(parsed);
      if (syncNow) {
        final result = await engine.drainPending();
        if (!mounted) return;
        if (result.done > 0) {
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
        } else if (result.lastError != null) {
          setState(() {
            _phase = ScanPhase.error;
            _message = result.lastError;
            _handled = false;
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

  Future<void> _resetToScan() async {
    _handled = false;
    _receiptId = null;
    _message = null;
    setState(() => _phase = ScanPhase.idle);
    await _initCamera();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final controller = _controller;
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
                  message: _message,
                  onRetry: () async {
                    setState(() => _phase = ScanPhase.processing);
                    final result =
                        await ref.read(syncEngineProvider).drainPending();
                    refreshMoneySurfaces(ref);
                    if (!mounted) return;
                    if (result.done > 0) {
                      setState(() {
                        _phase = ScanPhase.success;
                        _message = 'Synced ${result.done} receipt(s).';
                      });
                    } else if (result.lastError != null) {
                      setState(() {
                        _phase = ScanPhase.error;
                        _message = result.lastError;
                      });
                    } else {
                      setState(() {
                        _phase = ScanPhase.offline;
                        _message =
                            'Nothing to sync. Check Wi‑Fi/mobile data, then scan again.';
                      });
                    }
                  },
                ),
              ScanPhase.idle => const Center(child: CircularProgressIndicator()),
              ScanPhase.scanning => controller == null
                  ? const Center(child: CircularProgressIndicator())
                  : MobileScanner(
                      controller: controller,
                      fit: BoxFit.cover,
                      errorBuilder: (context, error) {
                        return JourneyStatePanel.error(
                          message:
                              'Camera error: ${error.errorDetails?.message ?? error.errorCode.name}',
                          onRetry: _resetToScan,
                        );
                      },
                      onDetect: (capture) {
                        if (_handled || _phase != ScanPhase.scanning) return;
                        final raw = capture.barcodes.firstOrNull?.rawValue;
                        if (raw == null || raw.isEmpty) return;
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
                      _phase != ScanPhase.offline &&
                      _phase != ScanPhase.permission) ...[
                    const SizedBox(height: 8),
                    Text(_message!),
                  ],
                  const Spacer(),
                  if (_phase == ScanPhase.scanning) ...[
                    FilledButton.tonalIcon(
                      onPressed: () => _handleRaw(
                        't=20240115T1200&s=250.00&fn=9281000100123456&i=12345&fp=987654321&n=1',
                        syncNow: false,
                      ),
                      icon: const Icon(Icons.cloud_off),
                      label: const Text('Save without sync (test)'),
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
