# Feature: live-truck-discovery

## Objective
Make the map discover trucks registered after the page has opened, so a simulator started later appears without a manual reload.

## Why
The map currently fetches `GET /trucks` only during boot. Its polling loop requests locations only for the initial in-memory list, so newly registered simulator trucks remain invisible.

## Scope
- IN: refresh the organization-scoped truck list during the existing polling cycle, preserve known telemetry/marker state for unchanged trucks, and add a static regression test.
- OUT: backend changes, simulator changes, route rendering, and authentication redesign.

## Constraints
- Keep the current Bearer authentication and organization scoping.
- Do not reset marker positions or history when refreshing the list.
- Preserve the existing first-load centering behavior.

## Delivery strategy
- Single work-unit bugfix commit.
- Delegated direct writer because implementation touches the map and tests.

## Tasks
- [x] T1: refresh and merge the truck list during polling. — `cargarCamiones()` now reconciles the organization-scoped list on every poll, reuses existing truck state, and cleans stale markers/movement state.
- [x] T2: add a regression test for live discovery. — `test_map_page_discovers_trucks_during_polling` covers polling refresh and state preservation/cleanup hooks.
- [x] T3: run the applicable checks and commit the fix. — static tests **22 passed**, `py_compile` passed, `make check` passed, `make test` **54 passed**, and `git diff --check` passed.

## Acceptance criteria
- Trucks registered after map boot appear on the next polling cycle.
- Existing truck telemetry, selection, markers, and history survive list refreshes.
- The first-load centering behavior remains unchanged.
- Existing checks and tests pass.

## Progress
- Implementation and verification complete; work-unit commit pending.

## Next Steps
- Create the work-unit commit, then reload or wait one polling interval in the map to observe newly registered trucks.

## Relevant Files
- source/static/map.html — map data loading and polling.
- tests/test_static.py — static contract tests.
