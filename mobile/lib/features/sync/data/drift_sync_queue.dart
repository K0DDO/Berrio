import 'package:drift/drift.dart';

import '../../../core/database/app_database.dart';
import '../domain/sync_job.dart';
import '../domain/sync_queue_repository.dart';

class DriftSyncQueueRepository implements SyncQueueRepository {
  DriftSyncQueueRepository(this._db);

  final AppDatabase _db;

  @override
  Future<SyncJob> enqueue({
    required String type,
    required String payloadJson,
    String? idempotencyKey,
  }) async {
    if (idempotencyKey != null) {
      final existing = await (_db.select(_db.syncQueueItems)
            ..where((t) => t.idempotencyKey.equals(idempotencyKey)))
          .get();
      final open = existing.where((e) => e.status != SyncStatus.done);
      if (open.isNotEmpty) {
        final row = open.first;
        // Re-scan / retry: pull failed or stuck jobs back into the queue.
        if (row.status != SyncStatus.pending) {
          await (_db.update(_db.syncQueueItems)
                ..where((t) => t.id.equals(row.id)))
              .write(
            const SyncQueueItemsCompanion(
              status: Value(SyncStatus.pending),
              retryCount: Value(0),
              lastError: Value(null),
            ),
          );
          final refreshed = await (_db.select(_db.syncQueueItems)
                ..where((t) => t.id.equals(row.id)))
              .getSingle();
          return _map(refreshed);
        }
        return _map(row);
      }
    }

    final id = await _db.into(_db.syncQueueItems).insert(
          SyncQueueItemsCompanion.insert(
            type: type,
            payload: payloadJson,
            status: SyncStatus.pending,
            idempotencyKey: Value(idempotencyKey),
          ),
        );
    final row = await (_db.select(_db.syncQueueItems)
          ..where((t) => t.id.equals(id)))
        .getSingle();
    return _map(row);
  }

  @override
  Future<List<SyncJob>> pending({int limit = 50}) async {
    // pending + stuck syncing + failed with retries left.
    final rows = await (_db.select(_db.syncQueueItems)
          ..where(
            (t) =>
                t.status.equalsValue(SyncStatus.pending) |
                t.status.equalsValue(SyncStatus.syncing) |
                (t.status.equalsValue(SyncStatus.failed) &
                    t.retryCount.isSmallerThanValue(5)),
          )
          ..orderBy([(t) => OrderingTerm.asc(t.createdAt)])
          ..limit(limit))
        .get();
    return rows.map(_map).toList(growable: false);
  }

  @override
  Future<void> markStatus(
    int id,
    SyncJobStatus status, {
    String? lastError,
    int? retryCount,
  }) async {
    await (_db.update(_db.syncQueueItems)..where((t) => t.id.equals(id))).write(
          SyncQueueItemsCompanion(
            status: Value(_toDrift(status)),
            lastError: Value(lastError),
            retryCount:
                retryCount != null ? Value(retryCount) : const Value.absent(),
          ),
        );
  }

  SyncJob _map(SyncQueueItem row) {
    return SyncJob(
      id: row.id,
      type: row.type,
      payloadJson: row.payload,
      status: _fromDrift(row.status),
      createdAt: row.createdAt,
      retryCount: row.retryCount,
      lastError: row.lastError,
      idempotencyKey: row.idempotencyKey,
    );
  }

  SyncStatus _toDrift(SyncJobStatus s) => switch (s) {
        SyncJobStatus.pending => SyncStatus.pending,
        SyncJobStatus.syncing => SyncStatus.syncing,
        SyncJobStatus.done => SyncStatus.done,
        SyncJobStatus.failed => SyncStatus.failed,
      };

  SyncJobStatus _fromDrift(SyncStatus s) => switch (s) {
        SyncStatus.pending => SyncJobStatus.pending,
        SyncStatus.syncing => SyncJobStatus.syncing,
        SyncStatus.done => SyncJobStatus.done,
        SyncStatus.failed => SyncJobStatus.failed,
      };
}
