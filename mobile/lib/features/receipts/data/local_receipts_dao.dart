import 'package:drift/drift.dart';
import 'package:uuid/uuid.dart';

import '../../../core/database/app_database.dart';

class LocalReceiptRecord {
  const LocalReceiptRecord({
    required this.id,
    required this.fn,
    required this.fd,
    required this.fp,
    required this.status,
    required this.synced,
    required this.createdAt,
    this.storeName,
    this.totalAmount,
    this.payloadJson,
  });

  final String id;
  final String fn;
  final String fd;
  final String fp;
  final String status;
  final bool synced;
  final DateTime createdAt;
  final String? storeName;
  final String? totalAmount;
  final String? payloadJson;
}

class LocalReceiptsDao {
  LocalReceiptsDao(this._db);

  final AppDatabase _db;
  static const _uuid = Uuid();

  Future<LocalReceiptRecord> upsertPending({
    required String fn,
    required String fd,
    required String fp,
    String? totalAmount,
    String? payloadJson,
  }) async {
    final existing = await (_db.select(_db.localReceipts)
          ..where((t) => t.fn.equals(fn) & t.fd.equals(fd) & t.fp.equals(fp)))
        .get();
    if (existing.isNotEmpty) {
      final row = existing.first;
      return _map(row);
    }

    final id = 'local_${_uuid.v4()}';
    await _db.into(_db.localReceipts).insert(
          LocalReceiptsCompanion.insert(
            id: id,
            fn: fn,
            fd: fd,
            fp: fp,
            totalAmount: Value(totalAmount),
            payloadJson: Value(payloadJson),
            status: const Value('local_pending'),
            synced: const Value(false),
          ),
        );
    final row = await (_db.select(_db.localReceipts)
          ..where((t) => t.id.equals(id)))
        .getSingle();
    return _map(row);
  }

  Future<void> markSynced({
    required String fn,
    required String fd,
    required String fp,
    required String serverId,
    String? status,
    String? storeName,
    String? totalAmount,
  }) async {
    final rows = await (_db.select(_db.localReceipts)
          ..where((t) => t.fn.equals(fn) & t.fd.equals(fd) & t.fp.equals(fp)))
        .get();
    if (rows.isEmpty) {
      await _db.into(_db.localReceipts).insert(
            LocalReceiptsCompanion.insert(
              id: serverId,
              fn: fn,
              fd: fd,
              fp: fp,
              status: Value(status ?? 'processed'),
              storeName: Value(storeName),
              totalAmount: Value(totalAmount),
              synced: const Value(true),
            ),
          );
      return;
    }
    final old = rows.first;
    await (_db.delete(_db.localReceipts)..where((t) => t.id.equals(old.id)))
        .go();
    await _db.into(_db.localReceipts).insert(
          LocalReceiptsCompanion.insert(
            id: serverId,
            fn: fn,
            fd: fd,
            fp: fp,
            status: Value(status ?? 'processed'),
            storeName: Value(storeName ?? old.storeName),
            totalAmount: Value(totalAmount ?? old.totalAmount),
            payloadJson: Value(old.payloadJson),
            synced: const Value(true),
          ),
        );
  }

  Future<List<LocalReceiptRecord>> listAll({int limit = 100}) async {
    final rows = await (_db.select(_db.localReceipts)
          ..orderBy([(t) => OrderingTerm.desc(t.createdAt)])
          ..limit(limit))
        .get();
    return rows.map(_map).toList(growable: false);
  }

  LocalReceiptRecord _map(LocalReceipt row) {
    return LocalReceiptRecord(
      id: row.id,
      fn: row.fn,
      fd: row.fd,
      fp: row.fp,
      status: row.status,
      synced: row.synced,
      createdAt: row.createdAt,
      storeName: row.storeName,
      totalAmount: row.totalAmount,
      payloadJson: row.payloadJson,
    );
  }
}
