# Confirm-first receipts & financial helper upgrade

See also: [architecture.md](architecture.md) · [api-receipts.md](api-receipts.md)

## Receipt flow

1. QR (camera or screenshot) or OCR text → draft receipt
2. OFD fetch when fiscal QR present (proverkacheka); never invent line items in stub
3. Always review on mobile (`ReceiptConfirmScreen`) when `needs_confirmation` or warnings
4. User edits store/date/lines/categories → `PATCH /receipts/{id}/confirm`
5. `save_as_draft: true` keeps `needs_confirmation`

Photos are **not** stored on the server. OCR runs on-device (`google_mlkit_text_recognition`); API receives text / fiscal params only. Paste-text fallback available.

## Line normalization

`LineItemNormalizer` strips SKUs/`№…`, title-cases, extracts volume/fat.  
`MerchantLineParser` + `merchant_receipt_templates` (loaded via `build_normalizer`) prepare per-store templates.

## Session & unlock

- Refresh token default: **180 days** (`REFRESH_TOKEN_EXPIRE_DAYS`)
- Devices: `device_id`, `device_name` on refresh tokens; `users.last_login_at`
- Mobile: biometric / PIN unlock via `local_auth` — password never stored for unlock

## Profile / health

- `GET/PATCH /users/me/profile` — monthly income, obligations, savings target
- Berrio Score uses these for contextual advice (no food-shaming on low income)

## Banks

- No bank login/password
- `POST /banks/statements/upload` (CSV / XLSX / PDF text)
- Reconciliation against receipts via existing engine
- `BankProvider` protocol for future Open Banking

## Analytics & AI

- `/analytics/summary` includes `top_merchants`, `avg_receipt`, previous period change
- AI: Kimi when `KIMI_API_KEY` set; stub labeled `[Локальный режим]`
- Logs: `ai.request` / `ai.response` / `ai.error` without PII
- Secondary: `GET /ai/monthly-review`
