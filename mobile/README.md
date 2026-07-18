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
# Prefer API_URL (VPS IP or domain). Legacy: API_BASE_URL.
flutter run --dart-define=API_URL=http://10.0.2.2:8000
# Physical device / VPS:
flutter run --dart-define=API_URL=http://YOUR_SERVER_IP
```

## Release APK

```bash
flutter build apk --release --dart-define=API_URL=http://YOUR_SERVER_IP
# Later: --dart-define=API_URL=https://api.berrio.com
# → build/app/outputs/flutter-apk/app-release.apk
```

LAN IP helper (Windows): `powershell -File scripts/print_lan_ip.ps1`

## Offline sync (Sprint 1)

- Domain: `features/sync`
- Queue statuses: `pending | syncing | done | failed`
- Runtime: in-memory repository
- Drift schema contract: `lib/core/database/app_database.dart` (DAO after codegen)
