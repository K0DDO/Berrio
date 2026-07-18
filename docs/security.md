# Security notes (Berrio)

## Field encryption

Sensitive strings (email today; more later) use `app.core.encryption.EncryptionService`:

- Algorithm: **AES-256-GCM**
- Key: `SHA-256(FIELD_ENCRYPTION_KEY or SECRET_KEY)` → 32 bytes
- Blob format: `version(1) || nonce(12) || ciphertext+tag`

Never use Fernet for new fields.

## Email storage

1. Normalize: `strip().lower()`
2. Lookup: `email_hash = SHA-256(pepper ‖ normalized_email)` UNIQUE
3. At rest: `email_enc = AES-GCM(normalized_email)`

Login/register find users **only** via `email_hash`.

## Auth tokens

| Token | Storage | Notes |
|-------|---------|-------|
| Access JWT | Client memory | Short TTL, `type=access` |
| Refresh | `HMAC-SHA256` hash in DB | Device-bound, rotated, reuse → revoke all |
| Email verify | `token_hash` + `expires_at` + `used_at` | One-time |
| Password reset | `token_hash` + `expires_at` + `used_at` | One-time; reuse rejected |

Logout requires a valid **Bearer** access token and matching `device_id` refresh.
