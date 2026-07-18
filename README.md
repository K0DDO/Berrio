# Berrio

AI financial assistant — personal accountant & economist.

> Helps you understand money before money starts managing you.

## Structure

```text
backend/   FastAPI modular monolith
mobile/    Flutter offline-first app
docs/      Product, architecture, ERD, sprints
```

## Quick start — Backend

```bash
cd backend
cp .env.example .env
# With Docker:
docker compose -f ../docker-compose.yml up --build
# Without Docker (local Postgres/Redis):
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

Health: `GET http://localhost:8000/health`

## Quick start — Mobile

Requires Flutter SDK.

```bash
cd mobile
flutter pub get
flutter run
```

## Documentation

- [Product philosophy](docs/product.md)
- [Architecture](docs/architecture.md)
- [ERD](docs/erd.md)
- [Auth API](docs/api-auth.md)
- [Security](docs/security.md)
- [Sprint 1](docs/sprints/sprint-01.md)
- [Sprint 2 — Auth](docs/sprints/sprint-02.md)
