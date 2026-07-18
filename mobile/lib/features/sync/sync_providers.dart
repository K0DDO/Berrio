import 'dart:convert';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/database/database_providers.dart';
import '../notifications/data/notifications_api.dart';
import '../receipts/data/local_receipts_dao.dart';
import '../receipts/data/receipts_api.dart';
import 'data/drift_sync_queue.dart';
import 'domain/sync_job.dart';
import 'domain/sync_queue_repository.dart';

export '../../core/database/database_providers.dart' show appDatabaseProvider;

abstract class SyncEngine {
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload);
  Future<void> enqueueNotificationRead(String notificationId);
  Future<int> drainPending();
  Future<void> syncWhenOnline();
}

/// Offline-first pipeline:
/// User action → Local database → Sync queue → Backend API → Mark synced.
class ReceiptSyncEngine implements SyncEngine {
  ReceiptSyncEngine(
    this._queue,
    this._localReceipts,
    this._receiptsApi,
    this._notificationsApi,
    this._connectivity,
  );

  final SyncQueueRepository _queue;
  final LocalReceiptsDao _localReceipts;
  final ReceiptsApi _receiptsApi;
  final NotificationsApi _notificationsApi;
  final Connectivity _connectivity;

  @override
  Future<void> enqueueReceiptScan(Map<String, dynamic> qrPayload) async {
    final key = '${qrPayload['fn']}_${qrPayload['fd']}_${qrPayload['fp']}';
    final payloadJson = jsonEncode({...qrPayload, 'idempotency_key': key});

    await _localReceipts.upsertPending(
      fn: qrPayload['fn'] as String,
      fd: qrPayload['fd'] as String,
      fp: qrPayload['fp'] as String,
      totalAmount: qrPayload['total_amount']?.toString(),
      payloadJson: payloadJson,
    );

    await _queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: payloadJson,
      idempotencyKey: key,
    );
  }

  @override
  Future<void> enqueueNotificationRead(String notificationId) async {
    await _queue.enqueue(
      type: 'NOTIFICATION_READ',
      payloadJson: jsonEncode({'id': notificationId}),
      idempotencyKey: 'notif_read_$notificationId',
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
          final receipt = await _receiptsApi.scan(payload);
          await _localReceipts.markSynced(
            fn: receipt.fn,
            fd: receipt.fd,
            fp: receipt.fp,
            serverId: receipt.id,
            status: receipt.status,
            storeName: receipt.storeName,
            totalAmount: receipt.totalAmount,
          );
        } else if (job.type == 'NOTIFICATION_READ') {
          final payload = jsonDecode(job.payloadJson) as Map<String, dynamic>;
          await _notificationsApi.markRead(payload['id'] as String);
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

  @override
  Future<void> syncWhenOnline() async {
    final result = await _connectivity.checkConnectivity();
    final offline = result.every((r) => r == ConnectivityResult.none);
    if (!offline) {
      await drainPending();
    }
  }
}

final syncQueueRepositoryProvider = Provider<SyncQueueRepository>((ref) {
  return DriftSyncQueueRepository(ref.watch(appDatabaseProvider));
});

final localReceiptsDaoProvider = Provider<LocalReceiptsDao>((ref) {
  return LocalReceiptsDao(ref.watch(appDatabaseProvider));
});

final syncEngineProvider = Provider<SyncEngine>((ref) {
  return ReceiptSyncEngine(
    ref.watch(syncQueueRepositoryProvider),
    ref.watch(localReceiptsDaoProvider),
    ref.watch(receiptsApiProvider),
    ref.watch(notificationsApiProvider),
    Connectivity(),
  );
});
