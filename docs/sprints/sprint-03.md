# Sprint 3 — Receipts + Offline Sync

## Goal

QR fiscal scan → backend receipt + line items; offline queue on device. **No photos.**

## Delivered

### Backend
- `POST /api/v1/receipts/scan` (fn, fd, fp, optional sum/date)
- `GET /api/v1/receipts`, `GET /api/v1/receipts/{id}`
- Idempotent unique `(user_id, fn, fd, fp)`
- Stub FNS client → store + items
- Events: `receipt.created`, `receipt.fetched`
- Migration `0003_receipts`

### Flutter
- QR fiscal parser (FNS query string)
- `sync_queue` → `ReceiptSyncEngine` posts to API
- Scan screen: offline enqueue + drain

### Tests
- `tests/test_receipts.py`
