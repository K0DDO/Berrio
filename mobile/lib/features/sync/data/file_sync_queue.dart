import 'dart:convert';
import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../domain/sync_job.dart';
import '../domain/sync_queue_repository.dart';

/// Durable file-backed queue (survives app restart).
/// Drift DAO replaces this after `build_runner` generates [AppDatabase].
class FileSyncQueueRepository implements SyncQueueRepository {
  FileSyncQueueRepository();

  List<SyncJob>? _cache;
  int _seq = 0;

  Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File(p.join(dir.path, 'berrio_sync_queue.json'));
  }

  Future<void> _ensureLoaded() async {
    if (_cache != null) return;
    final file = await _file();
    if (!await file.exists()) {
      _cache = [];
      return;
    }
    final raw = await file.readAsString();
    if (raw.trim().isEmpty) {
      _cache = [];
      return;
    }
    final list = jsonDecode(raw) as List<dynamic>;
    _cache = list.map((e) {
      final m = Map<String, dynamic>.from(e as Map);
      return SyncJob(
        id: m['id'] as int,
        type: m['type'] as String,
        payloadJson: m['payload'] as String,
        status: SyncJobStatus.values.byName(m['status'] as String),
        createdAt: DateTime.parse(m['created_at'] as String),
        retryCount: m['retry_count'] as int? ?? 0,
        lastError: m['last_error'] as String?,
        idempotencyKey: m['idempotency_key'] as String?,
      );
    }).toList();
    _seq = _cache!.fold<int>(0, (a, b) => a > b.id ? a : b.id);
  }

  Future<void> _persist() async {
    final file = await _file();
    final data = _cache!
        .map(
          (j) => {
            'id': j.id,
            'type': j.type,
            'payload': j.payloadJson,
            'status': j.status.name,
            'created_at': j.createdAt.toIso8601String(),
            'retry_count': j.retryCount,
            'last_error': j.lastError,
            'idempotency_key': j.idempotencyKey,
          },
        )
        .toList();
    await file.writeAsString(jsonEncode(data));
  }

  @override
  Future<SyncJob> enqueue({
    required String type,
    required String payloadJson,
    String? idempotencyKey,
  }) async {
    await _ensureLoaded();
    if (idempotencyKey != null) {
      final existing = _cache!.where(
        (j) =>
            j.idempotencyKey == idempotencyKey &&
            j.status != SyncJobStatus.done,
      );
      if (existing.isNotEmpty) return existing.first;
    }
    final job = SyncJob(
      id: ++_seq,
      type: type,
      payloadJson: payloadJson,
      status: SyncJobStatus.pending,
      createdAt: DateTime.now().toUtc(),
      idempotencyKey: idempotencyKey,
    );
    _cache!.add(job);
    await _persist();
    return job;
  }

  @override
  Future<List<SyncJob>> pending({int limit = 50}) async {
    await _ensureLoaded();
    return _cache!
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
    await _ensureLoaded();
    final index = _cache!.indexWhere((j) => j.id == id);
    if (index < 0) return;
    final current = _cache![index];
    _cache![index] = SyncJob(
      id: current.id,
      type: current.type,
      payloadJson: current.payloadJson,
      status: status,
      createdAt: current.createdAt,
      retryCount: retryCount ?? current.retryCount,
      lastError: lastError,
      idempotencyKey: current.idempotencyKey,
    );
    await _persist();
  }
}
