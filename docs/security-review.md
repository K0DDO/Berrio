# Production security review — Berrio

Date: 2026-07-18  
Scope: auth, family invites, API surface, mobile offline sync.

## Status: MVP hardened (continue before public launch)

| Area | Status | Notes |
|------|--------|-------|
| JWT access + refresh | OK | Access 15m; refresh hashed at rest |
| Password hashing | OK | Argon2id |
| Email at rest | OK | `email_hash` + AES-GCM `email_enc` |
| Family RBAC | OK | OWNER/PARENT/CHILD + permission matrix |
| Family invites | OK | Opaque token hashed; optional email lock; rate limit; audit |
| CORS | OK | Wildcard stripped when `debug=False` |
| Security headers | OK | nosniff, DENY frame, Referrer-Policy, HSTS (non-debug) |
| OpenAPI in prod | OK | `/docs` disabled when `debug=False` |
| Receipt photos | OK | Never accepted/stored |
| AI rate limit | OK | 60/hour/user |
| Invite rate limit | OK | 20/hour/user |
| Default secrets | WARN | Startup logs if `SECRET_KEY` / pepper still defaults |
| Global API rate limit | TODO | Edge / reverse-proxy recommended |
| WAF / bot protection | TODO | Deploy-time |
| Push notification auth | TODO | Channel interfaces only |
| Penetration test | TODO | Before public beta |

## Invite threat model

1. Token is shown once; only HMAC hash stored.
2. Optional `email_hash` lock prevents token forwarding to another account.
3. Cannot invite as `OWNER`.
4. Requires `can_invite_members` (owners always allowed).
5. Accept is idempotent-safe via unique membership constraint + conflict response.
6. Expired invites marked `EXPIRED` on use attempt.

## Deploy checklist

- [ ] Set strong `SECRET_KEY`, `EMAIL_HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`
- [ ] `APP_ENV=production`, `DEBUG=false`
- [ ] Explicit `CORS_ORIGINS` (no `*`)
- [ ] TLS termination + HSTS at edge
- [ ] Rotate JWT secrets with dual-key plan when needed
- [ ] Run Alembic through `0013_family_invites`
- [ ] Restrict DB network; least-privilege DB user

## Residual risks

- In-process rate limits reset on restart (use Redis/edge for multi-instance).
- Stub FNS / stub AI in environments without tokens.
- Child data scoping is permission-based; audit UI for accidental over-grant.
