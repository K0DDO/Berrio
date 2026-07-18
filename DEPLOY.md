# Deploy Berrio on a shared Ubuntu VPS

This guide fits a **server that already runs other Docker services** (Amnezia VPN, Telegram bots, etc.) and already has a **`deploy`** user — the same pattern as your more complex bot.

Repository: https://github.com/K0DDO/Berrio.git

Berrio is an **isolated Compose project** (`name: berrio`): own containers, own volumes, own bridge network. It must not share Postgres/Redis with the bots and must not fight Amnezia for VPN ports.

---

## Shared VPS model (recommended for you)

```
deploy@VPS
 ├── /opt/<your-complex-bot>/     # already yours via deploy
 ├── /opt/berrio/                 # same user, same style
 └── Docker
      ├── amnezia-* containers   # leave untouched
      ├── bot containers         # leave untouched
      └── berrio-*               # new project only
```

| Rule | Why |
|------|-----|
| Work as **`deploy`** | Same access model as the complex bot |
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

Postgres and Redis are **not** published on the host — no clash with other DBs.

Layout:

```
/opt/berrio/
├── docker-compose.production.yml
├── .env.production
├── scripts/{deploy,backup}.sh
├── backend/
└── deploy/nginx/berrio.conf

/opt/backups/berrio/          # dumps for this app only
```

---

## 0. Inventory (as `deploy` — do this first)

```bash
ssh deploy@SERVER_IP

whoami                    # expect: deploy
groups                    # expect: … docker …
docker ps --format 'table {{.Names}}\t{{.Ports}}\t{{.Status}}'
ss -tulpn | grep -E ':80|:443|:8000|:8080' || true
```

Note:

- Which ports are already taken (especially **80**, **443**, **8000**)
- Where the complex bot lives (e.g. `/opt/...`) — put Berrio next to it under `/opt/berrio`
- That Amnezia containers stay running after any change (`docker ps`)

If `deploy` is not in `docker` group, ask root once:

```bash
sudo usermod -aG docker deploy
# then re-login as deploy
```

---

## 1. Prepare folders (minimal — reuse existing user)

**Do not** run `adduser deploy` if the user already exists.

As `deploy` (or root only for mkdir/chown if needed):

```bash
sudo mkdir -p /opt/berrio /opt/backups/berrio
sudo chown -R deploy:deploy /opt/berrio /opt/backups/berrio
```

Packages only if missing:

```bash
# as root or via sudo — skip what you already have
sudo apt update
sudo apt install -y git curl
# nginx only if you will use it and :80 is free:
# sudo apt install -y nginx
```

Docker is already installed — **do not** re-run `get.docker.com`.

Confirm Compose plugin:

```bash
docker compose version
```

---

## 2. First deploy (as `deploy`)

```bash
ssh deploy@SERVER_IP
cd /opt
git clone https://github.com/K0DDO/Berrio.git berrio
cd /opt/berrio
```

If the repo already exists: `cd /opt/berrio && git pull`.

### 2.1 Secrets

```bash
cp .env.production.example .env.production
chmod 600 .env.production
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Fill at least: `SECRET_KEY`, `JWT_SECRET`, `EMAIL_HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, and replace `CHANGE_ME` in `DATABASE_URL` / `DATABASE_URL_SYNC`.

**Shared-VPS defaults in `.env.production`:**

```env
API_BIND=127.0.0.1
API_HOST_PORT=8000
ENABLE_API_DOCS=true
CORS_ORIGINS=["http://SERVER_IP","http://SERVER_IP:8000"]
```

If `8000` is already used by a bot:

```env
API_HOST_PORT=8088
```

Then health/docs become `http://127.0.0.1:8088/health` (and update nginx `proxy_pass` accordingly).

### 2.2 Start only Berrio

```bash
cd /opt/berrio
chmod +x scripts/*.sh

docker compose \
  -f docker-compose.production.yml \
  --env-file .env.production \
  up -d --build
```

This creates containers/volumes/networks prefixed by project **`berrio`**. Existing Amnezia/bot containers stay as they are.

### 2.3 Verify (without touching other stacks)

```bash
docker compose -f docker-compose.production.yml --env-file .env.production ps
docker ps --filter name=berrio

curl -fsS http://127.0.0.1:8000/health
# → {"status":"ok","service":"Berrio"}

# Still healthy?
docker ps --format '{{.Names}}' | head
```

Swagger (docs enabled): open via SSH tunnel from your PC if API is bound to localhost:

```bash
# on laptop
ssh -L 8000:127.0.0.1:8000 deploy@SERVER_IP
# browser: http://127.0.0.1:8000/docs
```

Or temporarily (smoke only):

```env
API_BIND=0.0.0.0
```

```bash
docker compose -f docker-compose.production.yml --env-file .env.production up -d
curl -fsS http://SERVER_IP:8000/health
# then set API_BIND=127.0.0.1 again
```

---

## 3. Nginx (optional on a busy host)

**Skip nginx** if:

- Amnezia or another panel already owns `:80` / `:443`, or
- you are fine with API on `API_HOST_PORT` + SSH tunnel / later domain

**Add nginx** only when `:80` is free or you can add a **separate** `server_name` without stealing `default_server`.

```bash
sudo cp /opt/berrio/deploy/nginx/berrio.conf /etc/nginx/sites-available/berrio
sudo sed -i "s/SERVER_IP/YOUR_REAL_IP/g" /etc/nginx/sites-available/berrio
# if API_HOST_PORT ≠ 8000, edit proxy_pass in that file
sudo ln -sf /etc/nginx/sites-available/berrio /etc/nginx/sites-enabled/berrio
sudo nginx -t && sudo systemctl reload nginx
```

Do **not** delete other sites in `sites-enabled` (bots / panels).

Later domain: change `server_name` → `api.berrio.com`, then certbot.

---

## 4. Firewall (careful)

Do **not** reset UFW. Only add what you need:

```bash
sudo ufw status
# usually SSH already allowed; Amnezia has its own ports — leave them

# only if you publish API publicly for a test:
# sudo ufw allow 8000/tcp

# only if nginx serves Berrio on :80 and http is not already open:
# sudo ufw allow http
```

With `API_BIND=127.0.0.1` you typically **do not** open `8000` in UFW.

---

## 5. Backups & deploy scripts

```bash
# as deploy
./scripts/backup.sh
# → /opt/backups/berrio/berrio_*.sql.gz (7 days)

crontab -e
15 3 * * * /opt/berrio/scripts/backup.sh >> /opt/backups/berrio/backup.log 2>&1
```

Update:

```bash
cd /opt/berrio && ./scripts/deploy.sh
```

(`backup → pull → build → migrate → up → health`, rollback on failure)

---

## 6. GitHub Actions (same `deploy` user)

Secrets:

| Secret | Value |
|--------|--------|
| `VPS_HOST` | Server IP |
| `VPS_USER` | **`deploy`** (existing) |
| `VPS_SSH_KEY` | Private key that already reaches `deploy` (or a new key appended to `~deploy/.ssh/authorized_keys`) |

If Actions already deploy your complex bot as `deploy`, reuse the same key **or** add a second key for Berrio — both are fine.

Ensure `/opt/berrio` is a git checkout that `deploy` can `git pull`.

Workflow: `.github/workflows/deploy.yml` → SSH → `/opt/berrio` → `./scripts`-style steps.

---

## 7. Mobile

```bash
# API published only on localhost → use nginx :80 or temporary public bind
flutter run --dart-define=API_URL=http://SERVER_IP:8000

# after nginx / domain
flutter run --dart-define=API_URL=http://SERVER_IP
flutter build apk --release --dart-define=API_URL=https://api.berrio.com
```

---

## 8. Coexistence checklist

- [ ] Logged in as **`deploy`**, member of `docker`
- [ ] `docker ps` still shows Amnezia + bots after Berrio `up`
- [ ] Berrio volumes named under project `berrio` (not shared with bots)
- [ ] Host port for API free or remapped (`API_HOST_PORT`)
- [ ] `API_BIND=127.0.0.1` in steady state
- [ ] UFW / Amnezia ports unchanged except intentional adds
- [ ] Backups under `/opt/backups/berrio` only

---

## 9. Useful commands

```bash
cd /opt/berrio
COMPOSE="docker compose -f docker-compose.production.yml --env-file .env.production"

$COMPOSE ps
$COMPOSE logs -f api worker
$COMPOSE down          # stops ONLY berrio — not Amnezia/bots
docker ps              # confirm others still up
```

---

## 10. Related files

| File | Purpose |
|------|---------|
| `docker-compose.production.yml` | Isolated prod stack |
| `.env.production.example` | Secrets + `API_BIND` / `API_HOST_PORT` |
| `scripts/deploy.sh` / `scripts/backup.sh` | Ops as `deploy` |
| `deploy/nginx/berrio.conf` | Optional reverse proxy |
| `.github/workflows/deploy.yml` | CD via `VPS_USER=deploy` |

Local development: `docs/local-development.md`.  
Clean-server path is the same stack; this doc prefers **reuse `deploy` + don’t touch VPN/bots**.
