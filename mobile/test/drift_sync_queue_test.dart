import 'package:drift/native.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:berrio/core/database/app_database.dart';
import 'package:berrio/features/sync/data/drift_sync_queue.dart';
import 'package:berrio/features/sync/domain/sync_job.dart';

void main() {
  late AppDatabase db;
  late DriftSyncQueueRepository queue;

  setUp(() {
    db = AppDatabase.forTesting(NativeDatabase.memory());
    queue = DriftSyncQueueRepository(db);
  });

  tearDown(() async {
    await db.close();
  });

  test('enqueue persists across repository instances', () async {
    final job = await queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: '{"fn":"1","fd":"2","fp":"3"}',
      idempotencyKey: '1_2_3',
    );
    expect(job.id, greaterThan(0));
    expect(job.status, SyncJobStatus.pending);

    final again = DriftSyncQueueRepository(db);
    final pending = await again.pending();
    expect(pending, hasLength(1));
    expect(pending.first.idempotencyKey, '1_2_3');
  });

  test('idempotency prevents duplicate open jobs', () async {
    await queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: '{}',
      idempotencyKey: 'same',
    );
    await queue.enqueue(
      type: 'RECEIPT_SCAN',
      payloadJson: '{}',
      idempotencyKey: 'same',
    );
    final pending = await queue.pending();
    expect(pending, hasLength(1));
  });

  test('markStatus done removes from pending', () async {
    final job = await queue.enqueue(type: 'RECEIPT_SCAN', payloadJson: '{}');
    await queue.markStatus(job.id, SyncJobStatus.done);
    expect(await queue.pending(), isEmpty);
  });
}
