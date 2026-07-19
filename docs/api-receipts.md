# Receipts API

Base: `/api/v1` · Auth: Bearer required · **Photos never accepted or stored.**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/receipts/scan` | Create/fetch from QR fiscal params (OFD) |
| POST | `/receipts/analyze-text` | OCR/pasted text → structured draft |
| PATCH | `/receipts/{id}/confirm` | User confirms/edits draft → `done` or draft |
| GET | `/receipts` | List current user receipts |
| GET | `/receipts/{id}` | Receipt detail + items + warnings |

## Scan body

```json
{
  "fn": "9281000100123456",
  "fd": "12345",
  "fp": "987654321",
  "purchased_at": "2024-01-15T12:00:00+03:00",
  "total_amount": "250.00",
  "qrraw": "t=20240115T1200&s=250.00&fn=...&i=12345&fp=...&n=1",
  "idempotency_key": "optional"
}
```

Idempotency: unique `(user_id, fn, fd, fp)`. Non-`done` receipts are re-processed on scan.

## Confirm body

```json
{
  "store_name": "Пятёрочка",
  "total_amount": "250.00",
  "purchased_at": "2024-01-15T12:00:00+03:00",
  "items": [{"name": "Молоко", "qty": "1", "price": "89", "sum": "89", "category_slug": "food"}],
  "confirm_as_is": false,
  "save_as_draft": false,
  "date_ignored": false,
  "date_confirmed": true
}
```

## Offline flow

```text
QR → local sync_queue (PENDING)
   → online drain → POST /receipts/scan
   → needs_confirmation | done
   → mobile ReceiptConfirmScreen when confirmation required
```

See also: [helper-upgrade.md](helper-upgrade.md).
