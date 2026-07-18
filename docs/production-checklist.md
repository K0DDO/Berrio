# Production checklist — Berrio beta

Use before inviting real test users or deploying to a VPS.

## 1. Secrets & environment

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] Strong `SECRET_KEY` (≥32 random bytes)
- [ ] Unique `EMAIL_HASH_PEPPER`
- [ ] `FIELD_ENCRYPTION_KEY` set (Fernet / AES material used by EncryptionService)
- [ ] No default values left from `.env.example`
- [ ] Secrets only via env / secret manager — never committed

## 2. Network & CORS

- [ ] Explicit `CORS_ORIGINS` (app origins only, no `*`)
- [ ] TLS at reverse proxy (Caddy / nginx / Traefik)
- [ ] HSTS enabled at edge
- [ ] Postgres / Redis not publicly reachable

## 3. Database

- [ ] `alembic upgrade head` through `0014_beta_hardening`
- [ ] Least-privilege DB role for the API
- [ ] Nightly `scripts/backup_postgres.sh` + offsite copy
- [ ] Restore drill once (`scripts/restore_postgres.sh`) — see below
- [ ] Disk monitoring on backup volume

### Backup / restore

```bash
export DATABASE_URL_SYNC=postgresql://berrio:***@127.0.0.1:5432/berrio
./backend/scripts/backup_postgres.sh /var/backups/berrio

# Restore (destructive)
./backend/scripts/restore_postgres.sh /var/backups/berrio/berrio_YYYYMMDD….sql.gz
alembic upgrade head
```

## 4. Rate limits & abuse

- [ ] AI chat: 60 req/hour/user (in-process)
- [ ] Family invites: 20 req/hour/user
- [ ] Edge rate limit recommended (e.g. 120 req/min/IP)
- [ ] Fail2ban / WAF optional for public beta

## 5. Logging & errors

- [ ] JSON logs when `DEBUG=false` (structlog)
- [ ] No PII in clear text in logs (prefer user ids / email hash prefixes)
- [ ] `/docs` disabled in production
- [ ] Health check: `GET /health`
- [ ] Alert on 5xx rate

## 6. Product / data quality

- [ ] Run `pytest tests/test_data_quality.py`
- [ ] Spot-check categorization on real receipts
- [ ] Confirm FNS token or accept stub for private beta
- [ ] Confirm Kimi key or stub AI

## 7. Mobile

- [ ] Release build against production API URL
- [ ] Camera permission copy reviewed
- [ ] Offline scan → sync path tested on device
- [ ] Onboarding → register → dashboard journey

## 8. Family & security

- [ ] Invite flow: create → accept → revoke
- [ ] Child role cannot see sibling data unexpectedly
- [ ] Review `docs/security-review.md`

## Sign-off

| Role | Name | Date |
|------|------|------|
| Backend | | |
| Mobile | | |
| Ops | | |
