import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:drift/drift.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/database/app_database.dart';
import '../../../core/database/database_providers.dart';
import '../../../core/network/dio_client.dart';

class NotificationDto {
  NotificationDto({
    required this.id,
    required this.type,
    required this.title,
    required this.message,
    required this.severity,
    required this.createdAt,
    this.readAt,
    this.payload = const {},
  });

  final String id;
  final String type;
  final String title;
  final String message;
  final String severity;
  final DateTime createdAt;
  final DateTime? readAt;
  final Map<String, dynamic> payload;

  bool get isRead => readAt != null;

  factory NotificationDto.fromJson(Map<String, dynamic> json) {
    return NotificationDto(
      id: json['id'] as String,
      type: json['type'] as String,
      title: json['title'] as String,
      message: json['message'] as String,
      severity: json['severity'] as String? ?? 'INFO',
      createdAt: DateTime.parse(json['created_at'] as String),
      readAt: json['read_at'] != null
          ? DateTime.parse(json['read_at'] as String)
          : null,
      payload: Map<String, dynamic>.from(json['payload'] as Map? ?? {}),
    );
  }
}

class NotificationsApi {
  NotificationsApi(this._dio);

  final Dio _dio;

  Future<List<NotificationDto>> list({bool unreadOnly = false}) async {
    final response = await _dio.get<List<dynamic>>(
      '/notifications',
      queryParameters: {'unread_only': unreadOnly},
    );
    return (response.data ?? [])
        .map((e) => NotificationDto.fromJson(Map<String, dynamic>.from(e as Map)))
        .toList();
  }

  Future<NotificationDto> markRead(String id) async {
    final response = await _dio.post<Map<String, dynamic>>('/notifications/$id/read');
    return NotificationDto.fromJson(response.data!);
  }
}

class LocalNotificationsDao {
  LocalNotificationsDao(this._db);

  final AppDatabase _db;

  Future<void> upsertAll(List<NotificationDto> items) async {
    for (final n in items) {
      await _db.into(_db.localNotifications).insertOnConflictUpdate(
            LocalNotificationsCompanion.insert(
              id: n.id,
              type: n.type,
              title: n.title,
              message: n.message,
              severity: Value(n.severity),
              payloadJson: Value(jsonEncode(n.payload)),
              createdAt: n.createdAt,
              readAt: Value(n.readAt),
              synced: const Value(true),
            ),
          );
    }
  }

  Future<List<NotificationDto>> listLocal() async {
    final rows = await (_db.select(_db.localNotifications)
          ..orderBy([(t) => OrderingTerm.desc(t.createdAt)]))
        .get();
    return rows
        .map(
          (r) => NotificationDto(
            id: r.id,
            type: r.type,
            title: r.title,
            message: r.message,
            severity: r.severity,
            createdAt: r.createdAt,
            readAt: r.readAt,
            payload: Map<String, dynamic>.from(
              jsonDecode(r.payloadJson) as Map? ?? {},
            ),
          ),
        )
        .toList();
  }

  Future<void> markReadLocal(String id, DateTime readAt) async {
    await (_db.update(_db.localNotifications)..where((t) => t.id.equals(id))).write(
          LocalNotificationsCompanion(readAt: Value(readAt)),
        );
  }
}

final notificationsApiProvider = Provider<NotificationsApi>((ref) {
  return NotificationsApi(ref.watch(dioProvider));
});

final localNotificationsDaoProvider = Provider<LocalNotificationsDao>((ref) {
  return LocalNotificationsDao(ref.watch(appDatabaseProvider));
});

/// Pull remote notifications into Drift, then expose local cache.
final notificationsListProvider =
    FutureProvider.autoDispose<List<NotificationDto>>((ref) async {
  final api = ref.watch(notificationsApiProvider);
  final dao = ref.watch(localNotificationsDaoProvider);
  try {
    final remote = await api.list();
    await dao.upsertAll(remote);
  } catch (_) {
    // Offline — serve Drift cache.
  }
  return dao.listLocal();
});
