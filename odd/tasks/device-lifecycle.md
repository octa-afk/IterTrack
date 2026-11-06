# GPS device lifecycle

Objective: administrators can provision, list, reassign, rotate the token of, and revoke GPS devices through the API instead of the local CLI, closing the last backend item of Phase 2.
Branch: `develop` | Delivery: one work unit, commits only with explicit user authorization | Test runner: `env/bin/python -m pytest tests/ -v`

## Specs

- **S1.** `POST /devices` (admin) creates a device and its open assignment to `truck_id`, and returns the plaintext token exactly once. Response `201`. Duplicate identifier → `400` `"Ya existe un dispositivo con ese identificador"`. Unknown truck → `404` `"Camión no encontrado"`. Inactive truck → `400` `"El camión está inactivo"`. Truck with an open assignment → `400` `"El camión ya tiene un dispositivo asignado"`.
- **S2.** `GET /devices` (admin) lists devices ordered by id with `id`, `identifier`, `active` and their open assignment (`truck_id`, `valid_from`) or `null`. It never exposes `token_hash`.
- **S3.** `POST /devices/{device_id}/reassign` (admin) body `{"truck_id": integer}` closes the current open assignment (`valid_to = now`) and opens a new one on the target truck. Response `200`. Unknown device → `404` `"Dispositivo no encontrado"`. Same truck → `400` `"El dispositivo ya está asignado a ese camión"`. Target truck already has an open assignment → `400` `"El camión ya tiene un dispositivo asignado"`.
- **S4.** `POST /devices/{device_id}/token/rotate` (admin) generates a new token, stores only its SHA-256 hash, and returns the plaintext once. The previous token stops authenticating immediately (`401` on `/devices/ingest`).
- **S5.** `POST /devices/{device_id}/revoke` (admin) sets `active = false` and closes the open assignment, so the truck can receive another device. A revoked device's token returns `401` on `/devices/ingest`.
- **S6.** Every endpoint in S1-S5 requires `role = "admin"`; a client account gets `403` `"Se requiere rol de administrador"`.
- **S7.** `scripts/provision_device.py` keeps working unchanged through the same service function.
- **S8.** Domain errors raised by the service are mapped to the HTTP status codes in S1-S5, and the CLI continues to print them as plain messages.

Assumptions (recorded, not user-confirmed):
- Any administrator manages any device, matching the organization endpoints. Device-to-organization scoping can come later with per-organization admins.
- Revoking is terminal in this iteration: there is no reactivate endpoint. Reprovisioning a revoked identifier stays blocked because identifiers are unique.
- Reassignment keeps the same token: the credential belongs to the hardware, not to the truck. Rotating is a separate explicit action.

## Tasks

- **T1** Domain errors and service functions in `source/services/devices.py` (`reassign_device`, `rotate_device_token`, `revoke_device`, open-assignment helper). Route: inline. Status: done.
- **T2** Schemas `source/schemas/device.py` + exports. Route: inline. Status: done.
- **T3** Admin endpoints in `source/services/devices.py`. Route: inline. Status: done.
- **T4** Tests `tests/test_devices_admin.py`. Route: inline. Status: done — 17 tests.
- **T5** Docs (`AGENTS.md`, `ROADMAP.md`). Route: inline. Status: done.
- **T6** Verification: `make check`, `make test`, end-to-end against the dev server. Route: inline. Status: done.

## Log

**L1 — User request (verbatim):** "que mas hay que implementar?" then "dale" (authorizing the recommended next item: GPS device lifecycle, the last pending Phase 2 backend item).

**L2 — Evidence (2026-10-23):**
- `make check` → ruff + mypy clean over 35 files.
- `make test` → 138 passed (121 before this feature).
- End-to-end against the dev server: `GET /devices` 200 empty; `POST /devices` 201 with token; duplicate identifier 400; reassign to truck 2 200; token rotation returned a different token; revoke 200 with `active: false` and no assignment; ingest with the revoked token 401; `GET /devices` as a client 403. Test device and its assignments deleted afterwards.
- No migration needed: `devices.active` and the partial unique indexes already existed.
- No commits made: the user has not authorized them for this feature.
