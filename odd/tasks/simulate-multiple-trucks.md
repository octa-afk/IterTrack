# Feature: simulate-multiple-trucks

## Objective
Extend `scripts/simulate_trucks.py` so it can register and move several trucks concurrently while preserving the existing single-truck invocation.

## Why
The map needs multiple simultaneous vehicles to exercise stable truck identity colors, filtering, and smooth movement with realistic telemetry.

## Scope
- IN: concurrent multi-truck simulation, deterministic truck configuration from CLI arguments, route phase offsets, shared authentication, graceful interruption, and automated tests for configuration/offset behavior.
- OUT: backend/API changes, frontend changes, route geometry redesign, and remote execution.

## Constraints
- Use `/home/octa/IterTrack/env/bin/python` for verification.
- Keep the existing API endpoints and authentication contract.
- Do not commit secrets or real credentials.
- Preserve the current single-truck CLI behavior.

## Delivery strategy
- Strategy: single work-unit commit for the simulator and its tests.
- Route: delegated direct writer because implementation touches multiple non-trivial files and needs preparation plus tests.

## Tasks
- [x] T1: add multi-truck configuration and concurrent simulation while preserving the legacy single-truck mode. — `--count/-n` defaults to one, authentication is shared, workers use deterministic identities and route offsets, and Ctrl+C stops the group.
- [x] T2: add deterministic tests for generated truck identities and route offsets. — `tests/test_simulate_trucks.py` covers identity preservation/derivation, evenly distributed offsets, and route rotation without network calls.
- [x] T3: run syntax checks and the complete applicable test suite. — focused tests **4 passed**, `py_compile` passed, `make check` passed, `make test` **53 passed**, and `git diff --check` passed.

## Acceptance criteria
- The default invocation continues to simulate one truck.
- A CLI option can start several trucks in one process.
- Each generated truck has a unique deterministic ID and plate.
- Trucks use different route starting offsets when possible.
- Authentication happens once and all workers reuse the resulting Bearer headers.
- Ctrl+C stops the worker group cleanly.
- Existing checks and new tests pass.

## Progress
- Implementation and verification complete; work-unit commit pending.

## Next Steps
- Create the authorized work-unit commit; later run the simulator against the API with a valid local account.

## Relevant Files
- scripts/simulate_trucks.py — simulator CLI and API worker logic.
- tests/test_simulate_trucks.py — simulator behavior tests.
