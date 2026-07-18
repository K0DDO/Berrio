# Berrio Mobile

Flutter offline-first client.

## Prerequisites

Install [Flutter SDK](https://docs.flutter.dev/get-started/install) and ensure `flutter` is on PATH.

## Bootstrap platform folders (first time)

```bash
cd mobile
flutter create . --project-name berrio --org com.berrio
flutter pub get
```

## Run

```bash
flutter run
# API on host from Android emulator:
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
```

## Offline sync (Sprint 1)

- Domain: `features/sync`
- Queue statuses: `pending | syncing | done | failed`
- Runtime: in-memory repository
- Drift schema contract: `lib/core/database/app_database.dart` (DAO after codegen)
