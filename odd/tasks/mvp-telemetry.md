# Feature: MVP telemetry fields

Locator: odd/tasks/mvp-telemetry.md (repo /home/octa/IterTrack, branch experiment/http)

## Objective

Persist and expose the MVP telemetry required by the roadmap:
- location (`lat`, `long`)
- speed in km/h
- heading in degrees from north

Keep the static frontend unchanged while making the API and simulator carry the complete telemetry payload.

## Problem

`TrackingPoint` currently stores only latitude and longitude. The simulator calculates speed and heading for console output but discards both values before calling the API.

## Why

The MVP scope explicitly requires location, speed, and direction so the tracking core can be validated independently of further visual polish.

## Scope

- Add validated `speed` and `heading` fields to the location input schema.
- Persist both fields in `TrackingPoint`.
- Add an Alembic migration with a safe default for existing rows.
- Update tracking creation and update endpoints to store telemetry.
- Update the simulator payload to send calculated telemetry.
- Add focused API and simulator tests.
- Leave `source/static/` unchanged.

## Constraints

- `speed` is non-negative and expressed in km/h.
- `heading` is expressed in degrees in the inclusive range 0–360.
- Preserve existing authentication and organization isolation.
- Use `/home/octa/IterTrack/env/bin/...` for Python/Alembic commands.
- Do not add dependencies.

## Tasks

- [x] T1: Add schema/model fields and Alembic migration.
- [x] T2: Wire telemetry through tracking endpoints and simulator.
- [x] T3: Add or update focused tests for persistence, validation, and simulator payloads.
- [x] T4: Run `make check && make test` and validate Alembic migration status.

## Acceptance Criteria

- `POST /trucks` accepts and persists speed and heading.
- `PUT /trucks/{truck_id}/location` accepts and persists speed and heading.
- Latest location and history responses include both telemetry fields.
- Invalid negative speed or out-of-range heading returns HTTP 422.
- Existing rows receive deterministic compatible values through the migration.
- The simulator sends calculated speed and heading instead of only printing them.
- Existing organization isolation and authentication tests remain green.

## Verification

- `make check && make test`
- `/home/octa/IterTrack/env/bin/alembic check`
- Structural readback of changed source and migration files.

## Route

- Implementation: delegated direct writer; multiple non-trivial source, migration, simulator, and test files require bounded implementation delegation.
- Trigger evidence: writer, preparation, and migration/test changes exceed the inline evidence budget.

## Progress

- Estado: completado
- Tareas completadas: 4/4
- Tests: `make check && make test` — 60 passed, 1 warning
- Migration: `env/bin/alembic check` — no new upgrade operations detected
- Commit: pendiente

## Next Step

Create the work-unit commit and leave the static frontend unchanged.
