# Berrio Backend

FastAPI modular monolith.

## Local run (no Docker)

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- Health: http://localhost:8000/health
- Modules map: http://localhost:8000/api/v1/system/modules
- OpenAPI: http://localhost:8000/docs

## Auth (Stage 2)

```bash
# tests (no Postgres required)
$env:PYTHONPATH = "."
.\.venv\Scripts\pytest tests/test_auth.py -v
```

API docs: [docs/api-auth.md](../docs/api-auth.md)

## Docker

```bash
docker compose up --build
# migrations run via entrypoint
docker compose exec api pytest tests/test_auth.py -v
```
