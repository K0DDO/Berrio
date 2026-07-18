# VPS deployment — Berrio beta

Target: single VPS (2 GB RAM+) with Docker + public HTTPS domain.

## 1. Server prep

```bash
# Ubuntu 24.04 example
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker $USER   # re-login
```

Point DNS `A` record of `api.yourdomain.com` → VPS IP.

## 2. Clone & secrets

```bash
git clone https://github.com/K0DDO/Berrio.git
cd Berrio
cp backend/.env.prod.example backend/.env.prod
# Fill SECRET_KEY, EMAIL_HASH_PEPPER, FIELD_ENCRYPTION_KEY, POSTGRES_PASSWORD, CORS_ORIGINS
```

Generate secrets:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set Caddy domain:

```bash
export BERRIO_DOMAIN=api.yourdomain.com
# Or edit deploy/Caddyfile and hardcode the host
```

## 3. Launch

```bash
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod up -d --build
docker compose -f docker-compose.prod.yml ps
curl -fsS https://api.yourdomain.com/health
```

Migrations run automatically via `entrypoint.prod.sh`.

## 4. Backups (cron)

```bash
# On the host (or a sidecar that can reach postgres)
0 3 * * * cd /opt/Berrio && \
  DATABASE_URL_SYNC=postgresql://berrio:***@127.0.0.1:5432/berrio \
  ./backend/scripts/backup_postgres.sh /var/backups/berrio
```

If Postgres is only on the Docker network, run backup inside the container:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > berrio_$(date -u +%Y%m%d).sql.gz
```

## 5. Flutter against production

```bash
cd mobile
flutter build apk --dart-define=API_BASE_URL=https://api.yourdomain.com
# iOS / physical Android — same dart-define
```

See `docs/device-testing.md`.

## 6. Update / rollback

```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

Rollback: checkout previous tag + rebuild. Restore DB from `docs/production-checklist.md` if needed.

## 7. Smoke checks

- [ ] `GET /health` → ok
- [ ] Register + login
- [ ] Scan receipt (stub or real FNS)
- [ ] Dashboard loads
- [ ] AI insights + feedback
- [ ] Family invite accept
- [ ] TLS certificate valid (Caddy auto)

## Firewall

Allow 22, 80, 443 only. Do **not** publish Postgres/Redis ports in prod compose.
