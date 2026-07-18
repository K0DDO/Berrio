# Auth API (Stage 2)

Base prefix: `/api/v1`

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | — | Create user + issue token pair |
| POST | `/auth/login` | — | Login + issue token pair |
| POST | `/auth/refresh` | — | Rotate refresh, new access |
| POST | `/auth/logout` | **Bearer required** | Revoke refresh for device |
| POST | `/auth/revoke-all` | Bearer | Revoke all refresh tokens |
| GET | `/auth/me` | Bearer | Current user profile |
| POST | `/auth/verify-email/request` | Bearer | Create verification token (email send later) |
| POST | `/auth/verify-email/confirm` | — | Confirm email with token |
| POST | `/auth/password-reset/request` | — | Issue reset token (no email enum) |
| POST | `/auth/password-reset/confirm` | — | Set new password + revoke sessions (one-time token) |

## Register / Login body

```json
{
  "email": "user@example.com",
  "password": "Secret123!",
  "display_name": "Dima",
  "device_id": "stable-device-uuid",
  "device_name": "Pixel 8"
}
```

`display_name` only on register.

## Token response

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "...",
    "email": "user@example.com",
    "display_name": "Dima",
    "email_verified": false,
    "created_at": "..."
  }
}
```

## Security notes

- Access JWT: short-lived (default 15m), `type=access`
- Refresh: opaque, stored as HMAC-SHA256 hash only, bound to `device_id`
- Rotation on every refresh; reuse of old token revokes **all** sessions
- Passwords: **Argon2id**
- Email lookup: `normalize(lowercase)` → `SHA-256(pepper ‖ email)` → `email_hash` UNIQUE
- Email at rest: `email_enc` via **AES-256-GCM** (`EncryptionService`)
- Password reset / email verify tokens: `token_hash` + `expires_at` + `used_at` (one-time)
