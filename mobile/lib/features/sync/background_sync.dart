import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'sync_providers.dart';

/// Listens for connectivity and drains the durable Drift sync queue.
class BackgroundSyncEngine {
  BackgroundSyncEngine(this._ref);

  final Ref _ref;
  StreamSubscription<List<ConnectivityResult>>? _sub;

  void start() {
    _sub ??= Connectivity().onConnectivityChanged.listen((results) async {
      final offline = results.every((r) => r == ConnectivityResult.none);
      if (!offline) {
        await _ref.read(syncEngineProvider).drainPending();
      }
    });
    // Kick once on start.
    unawaited(_ref.read(syncEngineProvider).syncWhenOnline());
  }

  Future<void> dispose() async {
    await _sub?.cancel();
    _sub = null;
  }
}

final backgroundSyncProvider = Provider<BackgroundSyncEngine>((ref) {
  final engine = BackgroundSyncEngine(ref);
  engine.start();
  ref.onDispose(engine.dispose);
  return engine;
});
