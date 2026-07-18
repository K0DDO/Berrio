import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'data/in_memory_sync_queue.dart';
import 'domain/sync_job.dart';
import 'domain/sync_queue_repository.dart';

/// Sync engine interface — drains queue when online (Stage 3 wires API).
abstract class SyncEngine {
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload);
  Future<int> drainPending();
}

class NoOpSyncEngine implements SyncEngine {
  NoOpSyncEngine(this._queue);

  final SyncQueueRepository _queue;

  @override
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload) async {
    await _queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: jsonEncode(qrPayload),
      idempotencyKey:
          '${qrPayload['fn']}_${qrPayload['fd']}_${qrPayload['fp']}',
    );
  }

  @override
  Future<int> drainPending() async {
    final pending = await _queue.pending();
    for (final job in pending) {
      await _queue.markStatus(job.id, SyncJobStatus.syncing);
      // Stage 3: POST to API, handle retries.
      await _queue.markStatus(job.id, SyncJobStatus.done);
    }
    return pending.length;
  }
}

final syncQueueRepositoryProvider = Provider<SyncQueueRepository>((ref) {
  return InMemorySyncQueueRepository();
});

final syncEngineProvider = Provider<SyncEngine>((ref) {
  return NoOpSyncEngine(ref.watch(syncQueueRepositoryProvider));
});
