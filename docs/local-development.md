# Local development — Berrio

Run the full stack on your PC for personal beta testing.

## Prerequisites

- Docker Desktop (Postgres + Redis + API + worker)
- Python 3.12+ (optional if you run API on host)
- Flutter SDK on PATH (`flutter doctor`)

## 1. Environment

```bash
cd backend
cp .env.local.example .env.local
# Edit SECRET_KEY / EMAIL_HASH_PEPPER if you want; defaults are fine for local beta
```

Required variables (empty values abort startup with a clear error):

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | JWT + token hashing |
| `EMAIL_HASH_PEPPER` | Email lookup hash |
| `DATABASE_URL` | Async Postgres |
| `DATABASE_URL_SYNC` | Alembic / backups |

Optional: `SEED_DEMO_DATA=true` creates `demo@berrio.app` / `Demo1234!` on API start.

## 2. Start backend (Docker)

From repo root:

```bash
docker compose up --build
```

Services:

| Service | Port | Role |
|---------|------|------|
| postgres | 5432 | Database |
| redis | 6379 | Cache / Celery broker |
| api | 8000 | FastAPI |
| worker | — | Celery worker |

Check:

```bash
curl http://localhost:8000/health
# OpenAPI (debug): http://localhost:8000/docs
```

Migrations run via `backend/scripts/entrypoint.sh` on API start.

### Seed demo data manually

```bash
# With API already up (development):
curl -X POST http://localhost:8000/api/v1/system/seed-demo

# Or CLI inside backend venv:
cd backend
.\.venv\Scripts\python.exe scripts\seed_demo.py
```

Demo login: **demo@berrio.app** / **Demo1234!**

## 3. Backend on host (alternative)

```bash
docker compose up postgres redis -d
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` is required so a phone on Wi‑Fi can reach the API.

## 4. Flutter

```bash
cd mobile
flutter pub get

# Android emulator → host machine
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000

# Physical phone on same Wi‑Fi (replace with your PC LAN IP)
flutter run --dart-define=API_BASE_URL=http://192.168.1.42:8000
```

Find LAN IP (Windows PowerShell):

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notmatch 'Loopback' } | Select-Object IPAddress, InterfaceAlias
```

See also [android-build.md](android-build.md) and [device-testing.md](device-testing.md).

## 5. Tests

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q

cd ../mobile
flutter analyze
flutter test
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Missing required environment variables` | Copy `.env.local.example` → `.env.local` |
| Phone cannot reach API | Use `--host 0.0.0.0`, same Wi‑Fi, Windows Firewall allow port 8000 |
| Cleartext HTTP blocked | Debug/release manifests already allow cleartext for local beta |
| Seed forbidden | Ensure `DEBUG=true` and `APP_ENV=development` |
