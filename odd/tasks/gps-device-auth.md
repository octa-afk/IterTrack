# GPS device authentication

## Objective
Each ESP32 authenticates with its own credential, independent of human JWT accounts, and can be manually assigned to a new truck without reflashing. Measurement time is recorded separately from reception time, so offline buffering can be supported later.

## Problem
Location endpoints require a human JWT (`get_current_user`). Devices cannot hold a human session, and the backend had no device identity, truck assignment, or measurement time.

## Decisions (confirmed)
- Provisioning is a local CLI (`scripts/provision_device.py`), not an HTTP endpoint, until roles exist. Devices are few, so no larger admin system.
- The token is random, shown once, and stored only as a SHA-256 hash. SHA-256 is intentional: tokens have high entropy, so bcrypt is not needed.
- The token belongs to the device. Truck assignment lives in `device_assignments` with validity intervals, so manual reassignment keeps the token while starting a distinct truck history.
- At most one open assignment per device and one per truck, enforced by partial unique indexes.
- Each tracking point stores `recorded_at` (measurement time) and `received_at` (server reception time). Existing rows were backfilled from `timestamp`.
- The simulator captures the measurement time at each reading and sends it as `recorded_at`. The API accepts it as optional; it requires a timezone and rejects future values beyond a 60 s tolerance. Without it, the server time is used.
- The MVP threat model is intentionally small: HTTPS, token confidentiality, hashed storage and basic operational validation are in scope; physical attacks and advanced firmware/software extraction are out of scope.
- A device batch is capped at 100 points. Points are processed independently so one bad point does not discard the rest of the batch.
- The device sends `recorded_at` and a sequence number. Idempotency is scoped to the assignment, so a manual reassignment can start a new truck history and reset the sequence.
- Rejected points are retained as raw evidence with their reason, device, assignment, batch, sequence and timestamps. Ingestion alerts expose a client-friendly summary while preserving technical details for analysis.
- Alerts group occurrences by organization, device and problem type while open. A closed alert that recurs creates a linked alert. Alert evidence is retained for at least one year from the latest related occurrence; open investigations are not removed automatically.

## Scope
Done:
- Slice 1 (`b3280ee`): models `Device` and `DeviceAssignment`, migration `3e8f1a6b9c2d`, token helpers, provisioning service and CLI, tests (87 passing with the rest of the suite).
- Time split (`95d5f13`): `recorded_at` and `received_at` on `tracking_points`, migration `7c3d9e1f2a4b`.
- Simulator measurement time (`678b343`): `recorded_at` sent with each ping; `PUT` accepts and validates it.
- Truck activation state: `Truck.active` defaults to true, migration `d4a7c9e2b6f1`, and human location writes reject inactive trucks.
- Ingestion core (`312b3cc`): `POST /devices/ingest`, device Bearer authentication, batches of 1–100 points, assignment attribution by `recorded_at`, partial acceptance, rejected raw evidence, and retry idempotency.

Pending:
- Reassignment: manually close the open assignment and create the new truck/history assignment; the device token remains unchanged.
- Token rotation and revocation.
- Device sends its GPS `recorded_at` from firmware; firmware offline buffer and discard policy (needs the expected outage duration).
- Simulator `registrar_camion` still sends no `recorded_at` for the first point.
- Restrict the existing human `PUT /location` once devices use their own endpoint, so human accounts cannot forge measurement times.

## Operational cases carried into slice 2
- The endpoint must handle empty, one-point, exactly-100-point and over-limit batches clearly.
- A malformed point must not discard valid points from the same batch.
- A retry after a timeout must not duplicate an already accepted point.
- A point without a covering assignment must be rejected and retained as evidence.
- The token is accepted only in the `Authorization` header and must not appear in logs or query strings.

## Checklist
- [x] DEV-1 Models `Device` and `DeviceAssignment` with partial unique indexes
- [x] DEV-2 Migration on top of `7c3d9e1f2a4b`
- [x] DEV-3 Token generation and SHA-256 hashing helpers
- [x] DEV-4 Provisioning service function and CLI
- [x] DEV-5 Tests: hash, provisioning, duplicate identifier, double open assignment per device and per truck
- [x] TIME-1 `recorded_at` / `received_at` split and migration
- [x] TIME-2 Simulator sends measurement time; API validates it
- [x] TIME-3 Read endpoints order by `recorded_at`; map speed history uses `recorded_at`
- [x] TRUCK-1 Add non-null `Truck.active` with a true default and migration
- [x] TRUCK-2 Reject human location writes for inactive trucks
- [x] INGEST-1 Device batch ingest endpoint
- [x] INGEST-2 Attribution by `recorded_at` and assignment-scoped idempotency (`batch_id` + `sequence`)
- [ ] INGEST-3 Create grouped client-facing alerts from rejected ingestion evidence
- [ ] REASSIGN-1 Manually close assignment and create a new truck/history assignment
- [ ] REVOKE-1 Device deactivation and token rotation

## Acceptance criteria (ingestion core complete; alert persistence pending)
- A device token is required; human JWT is not accepted on the device endpoint.
- Points are attributed to the truck valid at their `recorded_at`; a point with no covering assignment is rejected and retained.
- Replaying a batch creates no duplicates and reports each point's result.
- A batch with invalid points stores all valid points and retains raw rejected evidence; grouped alert persistence is pending INGEST-3.
- Inactive device or inactive truck is rejected.

## Checks
- `make test`, `make check`.
- Migrations verified upgrade/downgrade on PostgreSQL in a temporary schema (done for `7c3d9e1f2a4b` and `3e8f1a6b9c2d`).

## Progress
- Ingestion core is complete in `312b3cc`; focused tests (6), full suite (95), `make check`, and independent review all passed.
- Open decision for slice 2: device identifier at provisioning (MAC address proposed, not yet confirmed).
- Open decision for slice 2: exact retention policy for ordinary GPS points versus alert evidence.
- Contract confirmed for implementation: `POST /devices/ingest` accepts a device Bearer token and a JSON batch of up to 100 points; `batch_id` is a UUID per logical batch, `sequence` identifies a point within that batch, and retries are idempotent by assignment plus batch and sequence.

## Route
- Slice 1: delegated direct writer, verified by parent (tests, PostgreSQL migration check, diff review).
- Time split and simulator: direct inline with TDD.
- Slice 2 ingestion core: delegated direct writer; `tests/test_device_ingest.py` and the full suite pass. Alert persistence and grouping remain the next ingestion task because the repository had no alert schema.
- Next session: design and implement INGEST-3, then reassignment.
