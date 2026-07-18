# Sprint 2 — Auth

## Goal

Production-ready authentication for Berrio.

## Delivered

### Backend
- Register / login / logout / refresh / revoke-all / me
- JWT access + refresh rotation (hashed at rest, device-bound)
- Argon2id password hashing
- `users`, `refresh_tokens`, `audit_logs`
- Email verification + password reset tables & endpoints (email delivery not wired; debug tokens in DEBUG)

### Flutter
- Splash → login/register → shell
- Secure storage (refresh + device id)
- Dio interceptor with silent refresh

### Tests
- `tests/test_auth.py` — 10 cases (SQLite in-memory)

## Docker

```bash
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api pytest tests/test_auth.py -v
```

If Docker is not installed on the machine, run the same pytest suite locally (see backend README).
