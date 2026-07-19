#!/usr/bin/env bash
# Berrio production deploy on the VPS.
#
# Usage:
#   cd /opt/berrio && ./scripts/deploy.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"
PREV_SHA="$(git rev-parse HEAD)"

# Prefer API_HOST_PORT from .env.production when present
API_HOST_PORT="${API_HOST_PORT:-8000}"
if [[ -f "${ENV_FILE}" ]]; then
  _port="$(grep -E '^API_HOST_PORT=' "${ENV_FILE}" | tail -1 | cut -d= -f2- | tr -d '\r' || true)"
  if [[ -n "${_port}" ]]; then
    API_HOST_PORT="${_port}"
  fi
fi
HEALTH_URL="${HEALTH_URL:-http://127.0.0.1:${API_HOST_PORT}/health}"

compose() {
  docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" "$@"
}

health_check() {
  local i
  for i in $(seq 1 30); do
    if curl -fsS "${HEALTH_URL}" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
      echo "Health OK"
      return 0
    fi
    sleep 2
  done
  echo "Health check failed after retries" >&2
  return 1
}

rollback() {
  echo "==> Deploy failed — rolling back to ${PREV_SHA}"
  git reset --hard "${PREV_SHA}"
  compose build --pull
  compose up -d
  health_check || true
  exit 1
}

trap 'echo "ERROR at line $LINENO"; rollback' ERR

echo "==> Backup database"
"${ROOT}/scripts/backup.sh" || echo "WARN: backup skipped/failed (first deploy?)"

echo "==> git pull"
git pull --ff-only origin main

echo "==> Build images (no-cache api to avoid stale routes)"
compose build --pull --no-cache api worker

echo "==> Migrations (idempotent; also runs on api start)"
compose up -d postgres redis
compose run --rm --no-deps api alembic upgrade head

echo "==> Restart stack"
compose up -d --force-recreate --remove-orphans

echo "==> Health check"
health_check

echo "==> Verify statements upload route (expect 401, not 404)"
stmt_code="$(curl -sS -o /dev/null -w '%{http_code}' -X POST \
  "http://127.0.0.1:${API_HOST_PORT}/api/v1/banks/statements/upload" || true)"
echo "POST /banks/statements/upload → ${stmt_code}"
if [[ "${stmt_code}" == "404" ]]; then
  echo "Statements route missing in running container" >&2
  exit 1
fi

trap - ERR
echo "==> Deploy complete ($(git rev-parse --short HEAD))"
