# Receipts API (Stage 3)

Base: `/api/v1` · Auth: Bearer required · **Photos never accepted.**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/receipts/scan` | Create/fetch from QR fiscal params |
| GET | `/receipts` | List current user receipts |
| GET | `/receipts/{id}` | Receipt detail + items |

## Scan body

```json
{
  "fn": "9281000100123456",
  "fd": "12345",
  "fp": "987654321",
  "purchased_at": "2024-01-15T12:00:00Z",
  "total_amount": "250.00",
  "idempotency_key": "optional"
}
```

Idempotency is enforced by unique `(user_id, fn, fd, fp)`.

## Offline flow

```text
QR → local sync_queue (PENDING)
   → online drain → POST /receipts/scan → DONE
```
