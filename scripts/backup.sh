#!/usr/bin/env bash
# Berrio Postgres backup — keeps last 7 dumps under /opt/backups by default.
#
# Usage (on VPS from /opt/berrio):
#   ./scripts/backup.sh
#   BACKUP_DIR=/opt/backups ./scripts/backup.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-${ROOT}/docker-compose.production.yml}"
ENV_FILE="${ENV_FILE:-${ROOT}/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/berrio}"
KEEP_DAYS="${KEEP_DAYS:-7}"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing env file: ${ENV_FILE}" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="${BACKUP_DIR}/berrio_${STAMP}.sql"

echo "==> Backup → ${FILE}"

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T postgres \
  sh -c 'pg_dump -U "$POSTGRES_USER" --no-owner --no-acl "$POSTGRES_DB"' \
  > "${FILE}"

gzip -9 -f "${FILE}"
FILE_GZ="${FILE}.gz"
sha256sum "${FILE_GZ}" > "${FILE_GZ}.sha256"

find "${BACKUP_DIR}" -name 'berrio_*.sql.gz' -type f -mtime "+${KEEP_DAYS}" -delete
find "${BACKUP_DIR}" -name 'berrio_*.sql.gz.sha256' -type f -mtime "+${KEEP_DAYS}" -delete

echo "OK ${FILE_GZ}"
cat "${FILE_GZ}.sha256"
