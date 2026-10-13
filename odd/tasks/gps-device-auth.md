# GPS device authentication

## Objective
Each ESP32 authenticates with its own credential, independent of human JWT accounts, and can be reassigned between trucks without reflashing and without losing history. Measurement time is recorded separately from reception time, so offline buffering can be supported later.

## Problem
Location endpoints require a human JWT (`get_current_user`). Devices cannot hold a human session, and the backend had no device identity, truck assignment, or measurement time.

## Decisions (confirmed)
- Provisioning is a local CLI (`scripts/provision_device.py`), not an HTTP endpoint, until roles exist. Devices are few, so no larger admin system.
- The token is random, shown once, and stored only as a SHA-256 hash. SHA-256 is intentional: tokens have high entropy, so bcrypt is not needed.
- The token belongs to the device. Truck assignment lives in `device_assignments` with validity intervals, so reassignment does not change the token or the history.
- At most one open assignment per device and one per truck, enforced by partial unique indexes.
- Each tracking point stores `recorded_at` (measurement time) and `received_at` (server reception time). Existing rows were backfilled from `timestamp`.
- The simulator captures the measurement time at each reading and sends it as `recorded_at`. The API accepts it as optional; it requires a timezone and rejects future values beyond a 60 s tolerance. Without it, the server time is used.
- Planned for offline buffering: the device sends `recorded_at`, a per-device sequence number is used for idempotency, and the truck is attributed by the assignment valid at `recorded_at`.

## Scope
Done:
- Slice 1 (`b3280ee`): models `Device` and `DeviceAssignment`, migration `3e8f1a6b9c2d`, token helpers, provisioning service and CLI, tests (87 passing with the rest of the suite).
- Time split (`95d5f13`): `recorded_at` and `received_at` on `tracking_points`, migration `7c3d9e1f2a4b`.
- Simulator measurement time (`678b343`): `recorded_at` sent with each ping; `PUT` accepts and validates it.
- Truck activation state: `Truck.active` defaults to true, migration `d4a7c9e2b6f1`, and human location writes reject inactive trucks.

Pending:
- Slice 2: batch ingest endpoint for devices. Authenticate by token hash, resolve the truck by assignment at `recorded_at`, idempotent on `(device_id, sequence)`, reject inactive devices and trucks, and return a per-point result.
- Reassignment: close the open assignment and open a new one, in one transaction (CLI or admin endpoint once roles exist).
- Token rotation and revocation.
- Device sends its GPS `recorded_at` from firmware; firmware offline buffer and discard policy (needs the expected outage duration).
- Read endpoints ordering by `recorded_at` instead of `timestamp`.
- Simulator `registrar_camion` still sends no `recorded_at` for the first point.
- Restrict the existing human `PUT /location` once devices use their own endpoint, so human accounts cannot forge measurement times.

## Risks carried into slice 2
- Stolen device: revoke by deactivating the device (needs the revocation path above).
- Forged coordinates from a valid device: plausibility checks (jumps, speed vs. distance, time bounds) on the ordered-by-`recorded_at` sequence.
- Late batches after reassignment: attribution uses `recorded_at`, never the current assignment.
- Batch floods after long outages: maximum batch size and body size, rate limit per device, backoff in firmware.
- Token in logs or query strings: never accept it outside the `Authorization` header.

## Checklist
- [x] DEV-1 Models `Device` and `DeviceAssignment` with partial unique indexes
- [x] DEV-2 Migration on top of `7c3d9e1f2a4b`
- [x] DEV-3 Token generation and SHA-256 hashing helpers
- [x] DEV-4 Provisioning service function and CLI
- [x] DEV-5 Tests: hash, provisioning, duplicate identifier, double open assignment per device and per truck
- [x] TIME-1 `recorded_at` / `received_at` split and migration
- [x] TIME-2 Simulator sends measurement time; API validates it
- [x] TRUCK-1 Add non-null `Truck.active` with a true default and migration
- [x] TRUCK-2 Reject human location writes for inactive trucks
- [ ] INGEST-1 Device batch ingest endpoint
- [ ] INGEST-2 Attribution by `recorded_at` and idempotency
- [ ] REASSIGN-1 Close and open assignment in one transaction
- [ ] REVOKE-1 Device deactivation and token rotation

## Acceptance criteria (slice 2, not started)
- A device token is required; human JWT is not accepted on the device endpoint.
- Points are attributed to the truck valid at their `recorded_at`; a point with no covering assignment is rejected.
- Replaying a batch creates no duplicates and reports each point's result.
- Inactive device or inactive truck is rejected.

## Checks
- `make test`, `make check`.
- Migrations verified upgrade/downgrade on PostgreSQL in a temporary schema (done for `7c3d9e1f2a4b` and `3e8f1a6b9c2d`).

## Progress
- Session closed with slice 1, the time split, and truck activation state complete. Slice 2 is the next step.
- Open decision for slice 2: device identifier at provisioning (MAC address proposed, not yet confirmed).

## Route
- Slice 1: delegated direct writer, verified by parent (tests, PostgreSQL migration check, diff review).
- Time split and simulator: direct inline with TDD.
