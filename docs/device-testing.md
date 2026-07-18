# Real device testing — Berrio

## Point the app at your API

`ApiConfig.baseUrl` uses `--dart-define=API_BASE_URL=...`.

| Device | Example |
|--------|---------|
| Android emulator | `http://10.0.2.2:8000` (default) |
| iOS simulator | `http://127.0.0.1:8000` |
| Physical phone (LAN) | `http://192.168.x.x:8000` (PC LAN IP; HTTP cleartext may need Android network security / iOS ATS exception for debug) |
| Production VPS | `https://api.yourdomain.com` |

```bash
# Debug on physical Android (same Wi‑Fi as PC)
flutter run --dart-define=API_BASE_URL=http://192.168.1.42:8000

# Release APK against VPS
flutter build apk --dart-define=API_BASE_URL=https://api.yourdomain.com
```

## Device checklist (beta)

### Onboarding
- [ ] First launch → Welcome (value props)
- [ ] Register → lands on Dashboard
- [ ] Logout → Login works

### Receipt journey
- [ ] Camera permission granted
- [ ] Scan fiscal QR → processing → success
- [ ] Open receipt details (store, items, categories, price delta if any)
- [ ] Dashboard refresh shows new spend / AI card
- [ ] Airplane mode: offline scan queues → online sync drains

### Money surfaces
- [ ] Create goal → progress → dashboard updates
- [ ] Create budget
- [ ] Notifications list opens

### Family
- [ ] Create family
- [ ] Invite (copy token)
- [ ] Second device/account accepts invite
- [ ] Members list shows both roles

### AI
- [ ] Insights load with ids
- [ ] Helpful / Not helpful feedback succeeds

### Resilience
- [ ] Kill app mid-scan — no crash on relaunch
- [ ] Wrong API URL shows retryable error panel
- [ ] Pull-to-refresh on Home

## Capture for bugs

Note: device model, OS, `API_BASE_URL`, timestamp, screenshot, and `adb logcat` / Xcode console snippet.
