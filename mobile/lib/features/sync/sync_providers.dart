import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/network/dio_client.dart';
import '../../receipts/data/receipts_api.dart';
import 'data/in_memory_sync_queue.dart';
import 'domain/sync_job.dart';
import 'domain/sync_queue_repository.dart';

abstract class SyncEngine {
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload);
  Future<int> drainPending();
}

/// Offline-first: queue locally, push to API when [drainPending] runs.
class ReceiptSyncEngine implements SyncEngine {
  ReceiptSyncEngine(this._queue, this._receiptsApi);

  final SyncQueueRepository _queue;
  final ReceiptsApi _receiptsApi;

  @override
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload) async {
    final key = '${qrPayload['fn']}_${qrPayload['fd']}_${qrPayload['fp']}';
    await _queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: jsonEncode({...qrPayload, 'idempotency_key': key}),
      idempotencyKey: key,
    );
  }

  @override
  Future<int> drainPending() async {
    final pending = await _queue.pending();
    var done = 0;
    for (final job in pending) {
      await _queue.markStatus(job.id, SyncJobStatus.syncing);
      try {
        if (job.type == 'RECEIPT_SCAN') {
          final payload = jsonDecode(job.payloadJson) as Map<String, dynamic>;
          await _receiptsApi.scan(payload);
        }
        await _queue.markStatus(job.id, SyncJobStatus.done);
        done++;
      } on DioException catch (e) {
        await _queue.markStatus(
          job.id,
          SyncJobStatus.failed,
          lastError: e.message,
          retryCount: job.retryCount + 1,
        );
      } catch (e) {
        await _queue.markStatus(
          job.id,
          SyncJobStatus.failed,
          lastError: e.toString(),
          retryCount: job.retryCount + 1,
        );
      }
    }
    return done;
  }
}

final syncQueueRepositoryProvider = Provider<SyncQueueRepository>((ref) {
  return InMemorySyncQueueRepository();
});

final receiptsApiProvider = Provider<ReceiptsApi>((ref) {
  return ReceiptsApi(ref.watch(dioProvider));
});

final syncEngineProvider = Provider<SyncEngine>((ref) {
  return ReceiptSyncEngine(
    ref.watch(syncQueueRepositoryProvider),
    ref.watch(receiptsApiProvider),
  );
});
