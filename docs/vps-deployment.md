# VPS deployment — Berrio

> **Primary guide:** see root [`DEPLOY.md`](../DEPLOY.md) — shared VPS with existing `deploy` user (Amnezia / bots coexist), Docker Compose, optional nginx, GitHub Actions.

## Quick links

| Path | Purpose |
|------|---------|
| `docker-compose.production.yml` | IP / nginx-friendly production stack |
| `.env.production.example` | Secrets template |
| `deploy/nginx/berrio.conf` | Host nginx (replace `SERVER_IP`) |
| `.github/workflows/deploy.yml` | Auto-deploy on `main` |

## Alternate: Compose + Caddy (domain in-stack)

If you prefer TLS terminated by Caddy inside Compose (domain required):

```bash
cp backend/.env.prod.example backend/.env.prod
# fill secrets
export BERRIO_DOMAIN=api.yourdomain.com
docker compose -f docker-compose.prod.yml --env-file backend/.env.prod up -d --build
```

See also `docs/production-checklist.md`.
