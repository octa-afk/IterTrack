# Integrate the Mobile Fleet Map

## Objective
Use the user-provided mobile skeleton as the phone layout for `/map`, while keeping the existing authenticated API, telemetry state, Leaflet map, and desktop layout as the single source of truth.

## Problem and why
`source/static/map-mobile.html` is a standalone visual prototype: it creates synthetic trucks, fake telemetry, and a generic coordinate grid. Serving or copying it directly would show invented fleet data and disconnect mobile users from the real API. The current `map.html` already owns authentication, polling, Leaflet markers, and desktop behavior, but its mobile breakpoint does not provide the skeleton's tab-based mobile experience.

## Scope and constraints
- Implement in `source/static/map.html` and add/update contract tests in `tests/test_static.py` only.
- Treat `source/static/map-mobile.html` as a read-only visual reference; do not modify or remove it.
- Preserve existing uncommitted user changes in `source/static/map.html` and `tests/test_static.py`; do not reset or replace either file wholesale.
- Preserve desktop rendering and its existing API/auth flows.
- Mobile must reuse the existing live `trucks`, filters, selection, polling, token guard, and one Leaflet map instance. Do not copy the skeleton's mock data, simulated map grid, or animation loop.
- Do not invent unavailable driver, fuel, or route data. Omit those fields or display an explicit unavailable value.
- Preserve safe rendering of API-provided strings; do not inject them into HTML.

## Delivery plan
- Forecast: approximately 320 authored changed lines, excluding generated files.
- Strategy: `ask-on-risk` (default); no chain strategy is needed while the forecast remains below approximately 400 lines.
- Route: delegated direct. Evidence trigger: integrating a 487-line independent prototype with a 1,053-line live page and existing tests requires cross-file design and implementation.
- RDD status: disabled for this clone; use ordinary functional verification and do not start a native review.
- Test-first policy: applicable static contract tests exist. Observe a focused RED before implementation, then GREEN and refactor with tests remaining green. Runner: `env/bin/python -m pytest tests/test_static.py`.

## Tasks
- [x] MOB-1 — Integrate a live-data mobile layout into the existing map page.
  - Authorized scope: `source/static/map.html`, `tests/test_static.py`.
  - Acceptance: mobile tabs expose useful panel, fleet, and real map views; mobile map shows the existing Leaflet GPS markers and remains sized when revealed; auth/logout and existing desktop behavior remain intact; mobile data comes from live API state, with unavailable fields never fabricated; the prototype file remains untouched.
  - Checks: `env/bin/python -m pytest tests/test_static.py`; `make check`; `make test`; parent structural readback and `gentle-ai review assess` on the committed work-unit diff.
  - Progress/evidence: committed as `322bc372a9938d0d249713b4a992a04e238b102b` (`feat(map): add live mobile map views`). The committed diff also changes truck marker rendering to use DOM/textContent; parent readback found no simulated prototype data copied into the live page.
  - Route evidence: delegated because this integrates multiple UI/data flows and changes two non-trivial files.
  - Verification at MOB-1: focused RED run: 22 passed, 2 failed (new mobile-contract assertion plus existing marker-size assertion); GREEN: `env/bin/python -m pytest tests/test_static.py -k mobile_tabs` passed (1 passed, 23 deselected). `make check` passed; `make test` was 60 passed, 1 failed. The committed implementation used `[40,40]`; later local page changes use `[10,10]`, while the pre-existing test expects `[48,48]`.
  - Risk assessment: medium; `review_due: false`, reason `under_budget` for committed diff against `7c7d457`; untracked paths explicitly excluded.
  - Commit: `322bc372a9938d0d249713b4a992a04e238b102b`.
- [x] MOB-2 — Bring the mobile visual treatment closer to the supplied skeleton.
  - Authorized scope: `source/static/map.html`, `tests/test_static.py`.
  - Acceptance: mobile uses the prototype's translucent glass surfaces, floating map controls/cards, soft blue background, and bottom navigation treatment while retaining the actual Leaflet map and live data; desktop appearance is unchanged.
  - Checks: add a focused mobile visual-contract assertion and observe RED; run `env/bin/python -m pytest tests/test_static.py -k mobile`, `make check`, and `make test`.
  - Constraint: `source/static/map-mobile.html` stays read-only; do not copy its mock map or telemetry.
  - Progress/evidence: committed as `d6411fc5e5d6c07f549f7d7f03396028069282e7` (`feat(map): add mobile glass styling`). Mobile-only additions apply the supplied soft blue gradient, translucent blurred surfaces, floating map header/controls, and glass bottom tabs; desktop rules are unchanged.
  - Verification: RED — new glass-style assertion failed while the mobile integration contract passed; GREEN — `env/bin/python -m pytest tests/test_static.py -k mobile` passed (2 passed). `make check` passed. `make test` was 61 passed, 1 failed on the existing marker-size mismatch (expected 48x48, current local page 10x10); no marker-size change was made in this task.
  - Risk assessment: medium; `review_due: false`, reason `under_budget` for the committed diff against `322bc37`; untracked files explicitly excluded.
  - Route evidence: delegated because mobile styling interacts with the existing layout and test contract.
  - Commit: `d6411fc5e5d6c07f549f7d7f03396028069282e7`.

- [x] MOB-3 — Restore the mobile views and glass treatment in the current map page.
  - Authorized scope: `source/static/map.html`, `tests/test_static.py`.
  - Acceptance: restore the tested Panel/Camiones/Mapa tabs and responsive glass surfaces; keep logout reachable on mobile; use the existing authenticated fleet data and one Leaflet map; invalidate map size after revealing it; preserve desktop behavior and unrelated worktree changes.
  - Checks: `env/bin/python -m pytest tests/test_static.py -k 'mobile_tabs or mobile_glass_surfaces'`, `make check`, and `make test`.
  - Route: delegated direct; two non-trivial files and existing mobile behavior requires reading alongside implementation.
  - RDD status: disabled for this clone; ordinary functional verification only.
  - Test-first evidence: focused RED observed — 2 failed, 23 deselected. Failures confirm missing `mobile-tabs` and missing mobile glass CSS block.
  - Forecast: approximately 100 authored changed lines; delivery strategy remains `ask-on-risk`.
  - Verification: focused mobile tests passed (2 passed, 23 deselected); `make check` passed; `make test` passed (62 passed, one deprecation warning); parent focused spot check passed (2 passed, 23 deselected). Native assessment: medium, `review_due: false`, reason `under_budget`; RDD is disabled for this clone.
  - Result: restored mobile-only glass surfaces and floating controls, Panel/Flota/Mapa controls, a visible mobile logout action, and Leaflet size invalidation after showing the map. Existing authenticated data and one Leaflet instance are reused. Static marker label rendering remains via `textContent`.
  - Commit: pending work-unit commit.

## Next step
Record the work-unit commit identity in this document and synchronize the Engram mirror. Keep unrelated ROADMAP changes out of the commit.
