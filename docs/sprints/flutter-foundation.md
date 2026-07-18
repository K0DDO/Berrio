# Production gaps closed — Flutter + offline + QR + family RBAC

Closed before new finance features:

1. **Flutter foundation** — full project under `mobile/`: Auth (login/register/refresh),
   secure token storage, Dio JWT interceptors, Riverpod, Drift SQLite.
2. **Offline-first sync** — durable Drift `sync_queue_items` + `local_receipts`;
   flow: action → local DB → sync queue → API → mark synced. Survives app kill.
3. **QR receipt flow** — camera permission, `mobile_scanner`, scan → queue → history.
4. **Family security** — `FamilyPermissionChecker` on receipts, analytics, banks/transactions, AI.

## Next roadmap (suggested)

| Priority | Item | Status |
|----------|------|--------|
| 1 | Goals + Budgets modules (backend + Flutter screens) | In progress / this sprint |
| 2 | Notifications / explainable alerts | Next |
| 3 | Real FNS client (replace stub) when credentials available | Blocked on keys |
| 4 | IMAP bank ingestion (credentials) | Blocked on keys |
| 5 | Family invites + richer RBAC UI | Later |
| 6 | Receipt ↔ bank transaction reconciliation | Done (this sprint) |
