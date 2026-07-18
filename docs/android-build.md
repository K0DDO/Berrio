# Android build — Berrio

## Configuration already in place

- `INTERNET` permission — `android/app/src/main/AndroidManifest.xml`
- `CAMERA` for QR scan
- `android:usesCleartextTraffic="true"` — allows `http://LOCAL_IP:8000` during local beta
- Application id: `com.berrio.berrio`

## API base URL

Passed at build/run time (not baked into source as a secret):

```bash
# Emulator
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# Physical device → PC on LAN
flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000

# Release APK against local / LAN backend
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.x.x:8000

# Release against VPS
flutter build apk --release --dart-define=API_BASE_URL=https://api.yourdomain.com
```

Default without dart-define: `http://10.0.2.2:8000` (emulator).

## Release APK

```bash
cd mobile
flutter pub get
flutter build apk --release --dart-define=API_BASE_URL=http://YOUR_LAN_IP:8000
```

Output:

```text
build/app/outputs/flutter-apk/app-release.apk
```

Install on device:

```bash
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

Or copy the APK via USB / cloud and open it (allow install from unknown sources).

> Release signing currently uses the **debug** keystore (`build.gradle.kts`) so local beta installs work without a Play keystore. Replace before Play Store publish.

## Split / app bundle (optional)

```bash
flutter build appbundle --release --dart-define=API_BASE_URL=https://api.yourdomain.com
```

## Checklist before handing APK to testers

- [ ] Backend reachable on the URL in `API_BASE_URL`
- [ ] Firewall allows inbound TCP 8000 (if LAN HTTP)
- [ ] Demo account or invite testers to register
- [ ] Camera permission accepted on first scan
- [ ] Offline scan still queues when Wi‑Fi drops
