# Sprint 1 — Foundation (Berrio)

## Goal

Runnable skeleton: Docker Compose (when available), FastAPI health, Flutter shell with offline sync stubs, full docs. **No business logic.**

## Includes (architecture shelves)

Backend stub modules: `events` (EventBus Protocol + CeleryRedis stub), `notifications`, `goals`, `financial_health`, `budgets`, `merchants` (normalizer), `categorization` (engine), `audit`.

Flutter feature stubs: `goals`, `notifications`, `financial_health`, `budgets`, `sync` (in-memory `sync_queue` + Drift contract).

## DoD — Backend

- [x] FastAPI app + `GET /health`
- [x] Modular monolith layout
- [x] Stub modules listed above
- [x] EventBus Protocol + CeleryRedis stub publisher
- [x] Docker Compose: api, postgres, redis, worker
- [x] Alembic + initial `users` placeholder migration
- [x] pydantic-settings, `.env.example`, logging
- [x] README

## DoD — Flutter

- [x] Project under `mobile/`
- [x] go_router shell + placeholder screens
- [x] Feature folders including goals, notifications, financial_health, budgets, sync
- [x] Drift skeleton: `sync_queue`
- [x] Sync engine interface (no real upload)
- [x] Riverpod, theme, dio, secure storage wrappers
- [x] README

## DoD — Docs

- [x] `docs/product.md`
- [x] `docs/architecture.md`
- [x] `docs/erd.md`
- [x] this file

## Out of scope

JWT auth, FNS, real sync, AI, banks, push, score calc, budgets CRUD, merchant matching — later stages.

## Local notes

- Flutter SDK / Docker were not on PATH — run `flutter create . --project-name berrio` once SDK is installed; Compose is ready when Docker is available.
- Backend smoke-tested: `GET /health`, `GET /api/v1/system/modules`, `POST /api/v1/system/events/ping`.
