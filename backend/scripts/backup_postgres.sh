#!/usr/bin/env bash
# Postgres logical backup for Berrio.
# Usage:
#   DATABASE_URL_SYNC=postgresql://user:pass@host:5432/berrio ./scripts/backup_postgres.sh
#   ./scripts/backup_postgres.sh /var/backups/berrio
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-${ROOT}/backups}"
mkdir -p "${OUT_DIR}"

if [[ -z "${DATABASE_URL_SYNC:-}" ]]; then
  echo "DATABASE_URL_SYNC is required (postgresql://...)" >&2
  exit 1
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="${OUT_DIR}/berrio_${STAMP}.sql.gz"

echo "Backing up to ${FILE}"
pg_dump --no-owner --no-acl --format=plain "${DATABASE_URL_SYNC}" | gzip -9 > "${FILE}"

# Keep last 14 dumps in the target directory
ls -1t "${OUT_DIR}"/berrio_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f

echo "OK ${FILE}"
sha256sum "${FILE}" > "${FILE}.sha256"
cat "${FILE}.sha256"
