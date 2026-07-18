import 'dart:io';

import 'package:drift/drift.dart';
import 'package:drift/native.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

part 'app_database.g.dart';

enum SyncStatus { pending, syncing, done, failed }

class SyncQueueItems extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get type => text()();
  TextColumn get payload => text()();
  TextColumn get status => textEnum<SyncStatus>()();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();
  IntColumn get retryCount => integer().withDefault(const Constant(0))();
  TextColumn get lastError => text().nullable()();
  TextColumn get idempotencyKey => text().nullable()();
}

class LocalReceipts extends Table {
  TextColumn get id => text()(); // server UUID or local temp
  TextColumn get fn => text()();
  TextColumn get fd => text()();
  TextColumn get fp => text()();
  TextColumn get status => text().withDefault(const Constant('local_pending'))();
  TextColumn get storeName => text().nullable()();
  TextColumn get totalAmount => text().nullable()();
  TextColumn get payloadJson => text().nullable()();
  BoolColumn get synced => boolean().withDefault(const Constant(false))();
  DateTimeColumn get createdAt => dateTime().withDefault(currentDateAndTime)();

  @override
  Set<Column> get primaryKey => {id};
}

@DriftDatabase(tables: [SyncQueueItems, LocalReceipts])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(_openConnection());

  AppDatabase.forTesting(super.e);

  @override
  int get schemaVersion => 1;
}

LazyDatabase _openConnection() {
  return LazyDatabase(() async {
    final dir = await getApplicationDocumentsDirectory();
    final file = File(p.join(dir.path, 'berrio.sqlite'));
    return NativeDatabase.createInBackground(file);
  });
}
