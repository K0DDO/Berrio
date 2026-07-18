# Sprint 8 — Family + permissions

## Delivered

- `families`, `family_members`, `family_permissions` (`0007_families`)
- Roles: OWNER / PARENT / CHILD with default permission matrix
- `POST/GET /families`
- `GET /families/{id}/members`
- `PATCH /families/{id}/members/{member_id}/permissions`
- Family invites (`0013_family_invites`): create / list / revoke / accept
- Opaque invite token (hashed at rest), optional email lock, rate limit, audit
- Flutter Family screen: create, invite, accept token, members

## Security

See `docs/security-review.md` — headers, CORS harden, default-secret warnings.

## Next hardening

Child-only data scoping polish on shared budgets UI; Redis-backed rate limits.
