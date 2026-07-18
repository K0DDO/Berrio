# Deploy Berrio on a shared Ubuntu VPS

This guide fits a **server that already runs other Docker services** (Amnezia VPN, Telegram bots, etc.) and already has a **`deploy`** user — the same pattern as your more complex bot.

Repository: https://github.com/K0DDO/Berrio.git

Berrio is an **isolated Compose project** (`name: berrio`): own containers, own volumes, own bridge network. It must not share Postgres/Redis with the bots and must not fight Amnezia for VPN ports.

**App path (fixed):** `/opt/berrio`  
**Backups:** `/opt/backups/berrio`

---

## Shared VPS model

```
deploy@VPS
 ├── /opt/<your-complex-bot>/
 ├── /opt/berrio/              ← Berrio (owned by deploy)
 └── Docker: amnezia + bots + berrio (isolated)
```

| Rule | Why |
|------|-----|
| Work as **`deploy`** after root prepares `/opt/berrio` | Same access model as the complex bot |
| Do **not** recreate `deploy` / reinstall Docker | Avoid breaking Amnezia and bots |
| Do **not** `ufw --force reset` | Can lock you out or kill VPN ports |
| Prefer `API_BIND=127.0.0.1` | API not public next to VPN |
| Own host port if `8000` busy | `API_HOST_PORT=8088` (example) |
| Skip or carefully add nginx | `:80`/`:443` may already be used |

---

## Architecture

```
Internet (optional nginx :80)
   │
   ▼
127.0.0.1:API_HOST_PORT  →  berrio api (container :8000)
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
            berrio postgres  berrio redis   berrio worker
            (private net)    (private)      (Celery)
```

Layout:

```
/opt/berrio/
├── docker-compose.production.yml
├── .env.production
├── scripts/{deploy,backup}.sh
├── backend/
└── deploy/nginx/berrio.conf

/opt/backups/berrio/
```

---

## 0. Inventory (as `deploy`)

```bash
ssh deploy@SERVER_IP
whoami
groups
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ss -tulpn | grep -E ':80|:443|:8000|:8080' || true
```

---

## 1. Prepare `/opt/berrio` (as root / admin — once)

`deploy` normally cannot create `/opt` itself. Do this **once** as root:

```bash
ssh root@SERVER_IP   # or admin with sudo

sudo mkdir -p /opt/berrio /opt/backups/berrio
sudo chown -R deploy:deploy /opt/berrio /opt/backups/berrio
ls -la /opt | grep berrio
```

---

## 2. First deploy (as `deploy`)

```bash
ssh deploy@SERVER_IP
cd /opt/berrio
git clone https://github.com/K0DDO/Berrio.git .
# if folder already has a clone: git pull
```

If you previously cloned into `~/berrio`, move it:

```bash
rsync -a ~/berrio/ /opt/berrio/
rm -rf ~/berrio
cd /opt/berrio
```

### 2.1 Secrets

```bash
cp .env.production.example .env.production
chmod 600 .env.production
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
nano .env.production
```

Fill: `SECRET_KEY`, `JWT_SECRET`, `EMAIL_HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, replace `CHANGE_ME` in DB URLs, `CORS_ORIGINS`, `FNS_API_TOKEN` (optional), keep `API_BIND=127.0.0.1`.

### 2.2 Start

```bash
cd /opt/berrio
chmod +x scripts/*.sh
docker compose -f docker-compose.production.yml --env-file .env.production up -d --build
curl -fsS http://127.0.0.1:8000/health
docker ps
```

---

## 3. Nginx (optional)

```bash
sudo cp /opt/berrio/deploy/nginx/berrio.conf /etc/nginx/sites-available/berrio
sudo sed -i "s/SERVER_IP/YOUR_REAL_IP/g" /etc/nginx/sites-available/berrio
sudo ln -sf /etc/nginx/sites-available/berrio /etc/nginx/sites-enabled/berrio
sudo nginx -t && sudo systemctl reload nginx
```

---

## 4. Firewall

Do not reset UFW. Only add rules you need. With `API_BIND=127.0.0.1` you usually do **not** open `8000`.

---

## 5. Backups & deploy scripts

```bash
cd /opt/berrio
./scripts/backup.sh
# → /opt/backups/berrio/berrio_*.sql.gz

crontab -e
15 3 * * * /opt/berrio/scripts/backup.sh >> /opt/backups/berrio/backup.log 2>&1
```

```bash
cd /opt/berrio && ./scripts/deploy.sh
```

---

## 6. GitHub Actions

| Secret | Value |
|--------|--------|
| `VPS_HOST` | Server IP |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | Private key for `deploy` |

Workflow deploys to **`/opt/berrio`**.

---

## 7. Mobile

```bash
flutter run --dart-define=API_URL=http://SERVER_IP:8000
# later: https://api.berrio.com
```

---

## 8. Checklist

- [ ] `/opt/berrio` owned by `deploy:deploy`
- [ ] Amnezia + bots still up after `compose up`
- [ ] `API_BIND=127.0.0.1`
- [ ] Secrets only in `.env.production`
- [ ] Backups in `/opt/backups/berrio`

```bash
cd /opt/berrio
COMPOSE="docker compose -f docker-compose.production.yml --env-file .env.production"
$COMPOSE ps
$COMPOSE logs -f api
$COMPOSE down   # only Berrio
```

Related: `docker-compose.production.yml`, `.env.production.example`, `scripts/*`, `deploy/nginx/berrio.conf`, `.github/workflows/deploy.yml`.
