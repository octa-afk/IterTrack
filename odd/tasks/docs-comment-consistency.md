# Documentation and Code Comment Consistency

## Objective
Align user/developer documentation and tracking comments with the current implementation so instructions do not misstate authentication, registration, organization scope, routes, telemetry fields, or history behavior.

## Problem and why
Several documents describe an earlier API shape: they call protected truck reads public, omit required organization data from registration, and contain obsolete backend structure and roadmap status. Tracking comments also describe append-only history as if it replaced the current location. These mismatches can lead to failed requests or mistaken assumptions about data behavior.

## Scope and constraints
- Update only `README.md`, `ROADMAP.md`, `AGENTS.md`, `source/resumen.md`, and `source/services/tracking.py`.
- Preserve pre-existing local changes in `source/static/map.html`, `tests/test_static.py`, and untracked `opencode.json`.
- Keep API behavior unchanged; this task updates explanations and comments only.
- Use English for generated technical artifacts unless extending established Spanish project documentation/comments; use neutral, professional Spanish when updating those existing Spanish passages.
- No database, configuration, frontend, or endpoint behavior changes.

## Delivery plan
- Forecast: approximately 180 authored changed lines (additions plus deletions), excluding generated files.
- Strategy: `ask-on-risk` (default); no chain strategy is needed while the forecast remains below approximately 400 lines.
- Route: delegated direct. Evidence trigger: reconciling multiple documentation files and source comments against current code is broader than one inline evidence batch; implementation touches multiple non-trivial files.
- RDD status: disabled for this clone; ordinary verification applies, with no native review transaction.

## Tasks
- [ ] DOCS-1 — Reconcile repository documentation and tracking comments with implemented API behavior.
  - Authorized scope: the five files listed under Scope and constraints.
  - Acceptance: docs correctly describe Bearer authentication for tracking reads and writes, registration's organization-name/invitation-code either/or requirement, organization-scoped access, implemented versus pending roadmap scope, actual routes and telemetry fields, and simulator credential prerequisites; comments distinguish appending tracking points from returning the latest point and deleting history.
  - Checks: `make check`; `make test`; read back every edited file and confirm no behavior changes or edits outside the authorized scope.
  - Test-first exception: documentation and comment corrections have no meaningful deterministic RED test; existing functional suite is used as regression verification.
  - Progress/evidence: implementation committed as `7c7d457719495972781008ca6edc20aa7b748378` (`docs: align API and organization guidance with implementation`). Parent spot-check confirmed all five intended paths and no endpoint behavior changes.
  - Route evidence: delegated because this is a multi-file documentation/code-comment reconciliation; the writer read the authorized files before editing.
  - Verification: `make check` passed. `make test` was partial: 59 passed, 1 failed (`test_map_page_renders_truck_marker_design`, expected `iconSize:[48,48]`). The failure concerns pre-existing uncommitted map/test files, which were preserved; the full suite is not yet green.
  - Risk assessment: medium; `review_due: false`, reason `under_budget` for the committed diff against `31b998d`. The initial untracked inventory was explicitly excluded from the assessment.
  - Commit: `7c7d457719495972781008ca6edc20aa7b748378`.

## Next step
Resolve or independently reproduce the existing map-test failure without altering the preserved local changes, then rerun `make test` before marking DOCS-1 complete.
