# Invitation codes for client onboarding

Objective: only internal administrators create organizations; client users join an existing organization with an invitation code that admins can issue, inspect, rotate and revoke.
Branch: `develop` | Delivery: one work unit per task, commits only with explicit user authorization | Test runner: `env/bin/python -m pytest tests/ -v`

## Specs

- **S1.** New organizations are created only by administrators through `POST /organizations`. Body: `{"name": string, "expires_in_days": integer|null}`. Response `201` with the new organization and its generated invitation code. Duplicate name → `400` `"Ya existe una organización con ese nombre"`. Non-admin → `403`.
- **S2.** `GET /organizations` (admin only) lists organizations ordered by id, each with `id`, `name`, `invitation_code`, `invitation_expires_at`, `invitation_revoked_at`, `invitation_active`.
- **S3.** `GET /organizations/{org_id}/invitation` (admin only) returns the same shape for one organization. Unknown id → `404` `"Organización no encontrada"`.
- **S4.** `POST /organizations/{org_id}/invitation/rotate` (admin only) body `{"expires_in_days": integer|null}` generates a new code different from the previous one, clears `invitation_revoked_at`, and sets `invitation_expires_at` to `now + expires_in_days` days, or `null` when omitted.
- **S5.** `DELETE /organizations/{org_id}/invitation` (admin only) sets `invitation_revoked_at` to the current time and keeps the code. A revoked code is rejected at registration with `400` `"Código de invitación inválido"`.
- **S6.** An invitation whose `invitation_expires_at` is in the past is rejected at registration with `400` `"Código de invitación inválido"`.
- **S7.** `POST /auth/register` requires `invitation_code`; it no longer creates organizations from `org_name`. Missing code → `400` `"Debe proporcionar un código de invitación"`. Unknown, revoked or expired code → `400` `"Código de invitación inválido"`. A request that only sends `org_name` is treated as a missing code.
- **S8.** The register page only offers joining an existing organization with an invitation code: no "Crear empresa" mode and no organization-name field.
- **S9.** Organizations created before this change have `invitation_expires_at = null` and `invitation_revoked_at = null`, so their existing codes keep working.

Assumptions (recorded, not user-confirmed):
- One invitation code per organization, stored on `organizations`, instead of a separate multi-invitation table with per-code audit. This is the smallest model that supports issue/expire/revoke/rotate and can grow later.
- Any administrator may manage every organization, because administrators are internal company staff provisioning client fleets. There is no per-organization admin scoping yet.

## Tasks

- **T1** Model + migration: `Organization.invitation_expires_at`, `Organization.invitation_revoked_at`, `invitation_active` property. Route: inline. Status: done — migration `5426d9d8a15a`.
- **T2** Schemas: `OrganizationCreate`, `OrganizationResponse`, `InvitationRotate`, exports. Route: inline. Status: done.
- **T3** `source/services/organizations.py` admin endpoints + router registration in `main.py`. Route: inline. Status: done.
- **T4** `POST /auth/register` restricted to active invitations; `org_name` removed from `UserCreate`. Route: inline. Status: done.
- **T5** Backend tests: `tests/test_organizations.py` and `tests/test_auth.py` updates. Route: inline. Status: done — 14 new tests.
- **T6** Frontend: register page join-only, `UserCreate` type without `org_name`. Route: inline. Status: done.
- **T7** Docs: `AGENTS.md` and `ROADMAP.md`. Route: inline. Status: done.
- **T8** Verification: `make check`, `make test`, frontend lint + build. Route: inline. Status: done — ruff OK, mypy OK, 121 passed, oxlint OK, build OK.

## Log

**L1 — User request (verbatim):** "que es lo siguiente? / que sigue?" then "dale" (authorizing to start with invitations, the recommended next roadmap item: admin-issued invitation codes replacing free organization creation at registration).

**L2 — Evidence (2026-10-23):**
- `make check` → ruff + mypy clean.
- `make test` → 121 passed (107 before this feature).
- `npm --prefix frontend run lint` + `npm --prefix frontend run build` → OK.
- End-to-end against the dev server: admin login 200; `POST /organizations` 201; list 200; rotate 200 with a new code; register with the rotated code 201; revoke 200 (`invitation_active: false`); register with the revoked code 400 `"Código de invitación inválido"`; non-admin `GET /organizations` 403. Test organization and its user deleted afterwards.
- Migration applied to the dev database (`alembic upgrade head`).
- No commits made: the user has not authorized them for this feature.
