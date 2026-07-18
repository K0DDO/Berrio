/// Local sync job — device-only queue entity.
enum SyncJobStatus { pending, syncing, done, failed }

class SyncJob {
  const SyncJob({
    required this.id,
    required this.type,
    required this.payloadJson,
    required this.status,
    required this.createdAt,
    this.retryCount = 0,
    this.lastError,
    this.idempotencyKey,
  });

  final int id;
  final String type;
  final String payloadJson;
  final SyncJobStatus status;
  final DateTime createdAt;
  final int retryCount;
  final String? lastError;
  final String? idempotencyKey;
}
