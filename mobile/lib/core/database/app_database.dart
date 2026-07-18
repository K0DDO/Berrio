/// Drift schema for Berrio local DB (Sprint 1 contract).
///
/// After installing Flutter SDK:
///   1. Restore Drift `@DriftDatabase` implementation (see docs/architecture.md)
///   2. `dart run build_runner build --delete-conflicting-outputs`
///   3. Swap [InMemorySyncQueueRepository] → Drift-backed DAO
///
/// sync_queue columns:
///   id, type, payload, status (PENDING|SYNCING|DONE|FAILED),
///   created_at, retry_count, last_error, idempotency_key
library;

export '../../features/sync/domain/sync_job.dart' show SyncJobStatus;
