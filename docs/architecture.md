# Berrio — Architecture

## Stack

| Layer | Choice |
|-------|--------|
| Mobile | Flutter (offline-first, Drift/SQLite) |
| API | FastAPI (modular monolith) |
| DB | PostgreSQL 16 |
| Cache / broker | Redis |
| Workers | Celery |
| Infra | Docker Compose → VPS Linux |

## High-level

```text
Flutter App (Drift + Sync Queue)
        │
        ▼
   FastAPI /api/v1
        │
   ┌────┴────────────────────────────┐
   │ Domain modules (see below)      │
   │ EventBus ABC → Celery/Redis MVP │
   └────┬────────────────────────────┘
        │
   PostgreSQL · Redis · Workers
```

## Backend modules

| Module | Responsibility |
|--------|----------------|
| `auth` | JWT access + refresh rotation |
| `users` | Profile, settings |
| `families` | Family, roles, `family_permissions` |
| `categories` | Hierarchical categories |
| `categorization` | **Engine**: rules → user rules → AI |
| `receipts` | QR → FNS → items (no photo storage) |
| `products` | Product + ProductVariant + price history |
| `merchants` | **Merchant normalization** (aliases → canonical) |
| `transactions` | Bank/manual/receipt-linked txs |
| `banks` | Email parsers (pluggable adapters) |
| `budgets` | **Budget system** per category/period |
| `goals` | Financial goals |
| `analytics` | Aggregations |
| `financial_health` | Berrio Score |
| `notifications` | In-app / push / email channels |
| `ai` | Kimi-powered economist |
| `audit` | **audit_logs** (append-only) for sensitive actions |
| `events` | **EventBus Protocol/ABC** + domain events (Celery/Redis MVP) |

### Added before Sprint 1

1. **audit_logs** — append-only trail (`AuditService`)
2. **merchant normalization** — `merchants` + `merchant_aliases` (`MerchantNormalizer`)
3. **budget system** — `budgets` module + `BUDGET_WARNING` notifications
4. **EventBus abstraction** — `EventBus` Protocol; `CeleryRedisEventBus` impl
5. **categorization engine** — dedicated `CategorizationEngine` pipeline

## Event bus abstraction

Modules never import each other for side effects. They publish domain events via `EventBus`.

```text
EventBus (Protocol / ABC)
  ├── CeleryRedisEventBus   ← MVP
  └── (future) RabbitMqEventBus / KafkaEventBus
```

Example:

```text
ReceiptCreatedEvent
  → categorization
  → merchants (normalize store)
  → products / price_history
  → analytics
  → budgets (spend check)
  → notifications
  → financial_health (recalc trigger)
  → audit
```

Event packages: `receipt_events`, `transaction_events`, `goal_events`, `budget_events`, `user_events`.

## Categorization engine

Pipeline (deterministic first):

1. Exact / pattern **system rules**
2. **User rules** (from manual overrides)
3. Merchant → default category (if known)
4. **AI** fallback (Kimi)
5. User correction → persist new user rule

Owned by `modules/categorization`, not by receipts/transactions directly.

## Merchant normalization

Raw strings from banks/receipts (`PYATEROCHKA 1234`, `Пятёрочка`) map to a canonical `merchants` row via `merchant_aliases`. Enables matching bank tx ↔ receipt and stable analytics.

## Budget system

Budgets are period-bound limits (category or overall). Overspend emits `BUDGET_WARNING` notifications and feeds Berrio Score / AI.

## Audit logs

Append-only `audit_logs` for auth, permission changes, goal edits, reconciliation decisions, encryption key ops. No PII in clear text in `metadata` when avoidable — prefer IDs + hashed refs.

## Flutter offline-first

```text
UI → Domain → Drift (source of truth on device)
                → SyncQueue (PENDING|SYNCING|DONE|FAILED)
                → API when online
```

`sync_queue` lives **on device only**. Backend uses idempotency keys / unique receipt fingerprint `(user, fn, fd, fp)`.

## Security (foundation-ready)

- HTTPS in production
- JWT + refresh tokens (Stage 2)
- Field-level encryption for sensitive columns (Stage 2+)
- Secrets via env / secret manager
- No receipt photos stored

## Scaling path

Thousands of users: vertical VPS → managed Postgres/Redis → split workers → optional extract of `banks` / `ai` services using the same EventBus contracts.
