# GPS device authentication

## Objective
Each ESP32 authenticates with its own credential, independent of human JWT accounts, and can be reassigned between trucks without reflashing and without losing history.

## Problem
Location endpoints require a human JWT (`get_current_user`). Devices cannot hold a human session, and there is no device identity or truck assignment in the backend.

## Decisions (confirmed)
- Provisioning is a local CLI (`scripts/provision_device.py`), not an HTTP endpoint, until roles exist.
- The token is random, shown once, and stored only as SHA-256 hash.
- The token belongs to the device. Truck assignment lives in `device_assignments` with validity intervals.
- Only one open assignment per device and one open assignment per truck (partial unique indexes).

## Scope
- Slice 1 (this doc): models `Device`, `DeviceAssignment`; migration; token helpers; provisioning CLI; tests.
- Slice 2 (later): batch ingest endpoint with idempotency on `(device_id, sequence)`, attribution by `recorded_at` against assignment intervals, device/truck active checks.
- Out of scope now: HTTP admin endpoints, rotation/revocation API, roles, firmware.

## Checklist
- [x] DEV-1 Models `Device` and `DeviceAssignment` with partial unique indexes
- [x] DEV-2 Migration `on top of 7c3d9e1f2a4b`
- [x] DEV-3 Token generation and SHA-256 hashing helpers
- [x] DEV-4 Provisioning service function + CLI (`scripts/provision_device.py`)
- [x] DEV-5 Tests: hash, provisioning, duplicate identifier, double open assignment per device and per truck

## Acceptance criteria
- Token is never persisted in plaintext.
- Provisioning a device to a truck creates exactly one open assignment.
- Inserting a second open assignment for the same device or truck fails at the database level.

## Checks
- `make test`, `make check`.
- Migration verified upgrade/downgrade on PostgreSQL in a temporary schema.

## Progress
- Slice 1 done: DEV-1 to DEV-5 verified (87 tests; migration checked on PostgreSQL in a temporary schema).

## Route
- Delegated direct writer (2+ non-trivial files). Parent verifies with `make test` and reviews the diff.
