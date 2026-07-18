#!/bin/sh
set -e

echo "Waiting for Postgres..."
python - <<'PY'
import os, sys, time
import sqlalchemy as sa

url = os.environ.get("DATABASE_URL_SYNC") or os.environ.get("DATABASE_URL", "")
url = url.replace("postgresql+asyncpg://", "postgresql://")
if not url:
    print("DATABASE_URL_SYNC is required", file=sys.stderr)
    sys.exit(1)

for attempt in range(60):
    try:
        eng = sa.create_engine(url, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        print("Postgres is ready")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"  attempt {attempt + 1}/60: {exc}")
        time.sleep(1)
print("Postgres did not become ready in time", file=sys.stderr)
sys.exit(1)
PY

echo "Running migrations..."
alembic upgrade head
echo "Migrations complete."

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
