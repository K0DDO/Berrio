import 'sync_job.dart';

/// Abstraction over Drift-backed queue — swap impl without touching UI.
abstract class SyncQueueRepository {
  Future<SyncJob> enqueue({
    required String type,
    required String payloadJson,
    String? idempotencyKey,
  });

  Future<List<SyncJob>> pending({int limit = 50});

  Future<void> markStatus(
    int id,
    SyncJobStatus status, {
    String? lastError,
    int? retryCount,
  });
}
