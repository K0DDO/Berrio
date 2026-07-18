import '../domain/sync_job.dart';
import '../domain/sync_queue_repository.dart';

/// In-memory queue for Sprint 1 — replaced by Drift DAO after codegen.
class InMemorySyncQueueRepository implements SyncQueueRepository {
  final List<SyncJob> _jobs = [];
  int _seq = 0;

  @override
  Future<SyncJob> enqueue({
    required String type,
    required String payloadJson,
    String? idempotencyKey,
  }) async {
    final job = SyncJob(
      id: ++_seq,
      type: type,
      payloadJson: payloadJson,
      status: SyncJobStatus.pending,
      createdAt: DateTime.now().toUtc(),
      idempotencyKey: idempotencyKey,
    );
    _jobs.add(job);
    return job;
  }

  @override
  Future<List<SyncJob>> pending({int limit = 50}) async {
    return _jobs
        .where((j) => j.status == SyncJobStatus.pending)
        .take(limit)
        .toList(growable: false);
  }

  @override
  Future<void> markStatus(
    int id,
    SyncJobStatus status, {
    String? lastError,
    int? retryCount,
  }) async {
    final index = _jobs.indexWhere((j) => j.id == id);
    if (index < 0) return;
    final current = _jobs[index];
    _jobs[index] = SyncJob(
      id: current.id,
      type: current.type,
      payloadJson: current.payloadJson,
      status: status,
      createdAt: current.createdAt,
      retryCount: retryCount ?? current.retryCount,
      lastError: lastError,
      idempotencyKey: current.idempotencyKey,
    );
  }
}
