#!/usr/bin/env bash
# Restore Berrio Postgres from a gzipped pg_dump.
# WARNING: destructive — drops and recreates public schema objects via dump.
#
# Usage:
#   DATABASE_URL_SYNC=postgresql://user:pass@host:5432/berrio \
#     ./scripts/restore_postgres.sh ./backups/berrio_20260718T120000Z.sql.gz
set -euo pipefail

DUMP="${1:-}"
if [[ -z "${DUMP}" || ! -f "${DUMP}" ]]; then
  echo "Usage: $0 <backup.sql.gz>" >&2
  exit 1
fi
if [[ -z "${DATABASE_URL_SYNC:-}" ]]; then
  echo "DATABASE_URL_SYNC is required" >&2
  exit 1
fi

if [[ -f "${DUMP}.sha256" ]]; then
  echo "Verifying checksum…"
  sha256sum -c "${DUMP}.sha256"
fi

echo "Restoring ${DUMP} → ${DATABASE_URL_SYNC}"
echo "This will overwrite data. Continuing in 3s…"
sleep 3

gunzip -c "${DUMP}" | psql "${DATABASE_URL_SYNC}"
echo "Restore complete. Run: alembic upgrade head"
