# Testing guide — Berrio

## Backend

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

### Data quality suite

Fixtures: `tests/fixtures/beta_dataset.py`

```bash
pytest tests/test_data_quality.py -q
```

Covers:

| Check | What |
|-------|------|
| Merchant normalization | Alias → canonical store names |
| Categorization accuracy | ≥75% on seeded line items |
| Product normalization | Brand / volume parse + shared variant |
| Price history | Second purchase updates last price |
| Reconciliation confidence | Exact merchant/amount scores high |
| API scan | Stub FNS items categorized + product-linked |

Export fixtures JSON (optional):

```bash
python -m scripts.export_beta_fixtures
```

### AI feedback

```bash
# After register + scan + GET /ai/insights
POST /api/v1/ai/insights/{id}/feedback
{ "feedback_type": "HELPFUL" }   # or NOT_HELPFUL
```

### Family invites

`tests/test_family_invites.py` — create, email-lock, accept, revoke.

## Flutter

```bash
cd mobile
flutter analyze
flutter test
```

Key unit tests: QR parser, Drift sync queue, DTO parsers (dashboard, receipts, notifications).

Manual device checklist:

1. Welcome → Register → Dashboard
2. Scan QR (or simulate offline) → success → receipt details
3. Goal update → dashboard refresh
4. Family create → invite token → accept on second account
5. Airplane mode scan → reconnect → sync

## CI suggestion

- Backend pytest on PR
- Flutter analyze + test on PR
- Nightly: backup script dry-run against staging DB
