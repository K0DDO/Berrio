#!/usr/bin/env bash
# Verify Auth stage inside Docker Compose.
set -euo pipefail
cd "$(dirname "$0")/.."

docker compose up -d --build postgres redis
docker compose up -d --build api
docker compose exec -T api alembic upgrade head
docker compose exec -T api pytest tests/test_auth.py -v
echo "Auth Docker verification OK"
