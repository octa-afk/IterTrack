# React frontend migration
Branch: feat/telemetry-contract-hardening
Delivery: incremental work-unit commits
Test runner: `make test && make check`; `npm run build` from Fase 2 onward.

Strategy: modularize the vanilla HTML into CSS files and native ES modules first,
then port those modules into React components 1:1. The first attempt (single
monolithic `App.tsx`, commits `035d82b`..`fc52895`) was reverted in `8eb1580`.

## Specs

1. **S1 — Target:** migrate the frontend to React + TypeScript + Vite, preserving the FastAPI API surface, JWT key `itertrack_token`, routes `/`, `/map`, `/register`, organization isolation, and current user-visible behavior. Status: reopened; no implementation on disk as of `8eb1580`.
2. **S2 — HTML modularization first:** "comencemos modularizando primero el html". Split the monolithic static pages into dedicated CSS files and native ES modules (`<script type="module">`), with no build step. Layout, styling, and behavior must stay identical to the current vanilla pages. `map.html` markup must end up free of inline `<style>` and application `<script>` blocks.
3. **S3 — Tests decoupled from markup internals:** `tests/test_static.py` must assert observable behavior (skeleton ids, auth wiring, navigation) and asset serving, not inline CSS values embedded in the HTML response. This removes the blocker that would otherwise fail every modularization step.
4. **S4 — Checks:** `make test` and `make check` green at the end of every task, plus a manual smoke of `/`, `/map`, and `/register` against the running dev server.

## Tasks

- T1 (S1): Scaffold React + TypeScript + Vite and migrate login/register flows. Superseded — reverted in `8eb1580`.
- T2 (S1): Migrate the authenticated map dashboard and Leaflet integration. Superseded — reverted in `8eb1580`.
- T3 (S1): Switch FastAPI static serving to the React build. Superseded — reverted in `8eb1580`.
- T4 (S2, S3): Extract all inline CSS from the four static pages into `source/static/css/`, add the `/static` mount in FastAPI, and repoint the static tests at the served CSS instead of the HTML body. Route: inline. Status: complete. Commit: dda1f26.
- T5 (S2, S3): Extract the `map.html` application script into native ES modules under `source/static/js/`, one module per existing responsibility. Route: inline. Status: complete; session, API boundary, explicit store, truck synchronization, telemetry, selection, movement, charts, list, marker, and detail rendering all extracted.
- T6 (S2, S3, S4): Move the sidebar-toggle IIFE into a module, run the full suite, and smoke `/`, `/map`, `/register` in the browser. Route: inline. Status: complete.
- T7 (S1, S2): Scaffold Vite + React + TS, reusing `css/tokens.css`, with router and typed API client. Route: inline. Status: pending.
- T8 (S1): Port the shell (sidebar, topbar, mobile tabs) as components. Route: inline. Status: pending.
- T9 (S1): Port fleet list, filters, and detail card. Route: inline. Status: pending.
- T10 (S1): Port the map view, markers, and history chart. Route: inline. Status: pending.
- T11 (S1): Port bars and fleet summary. Route: inline. Status: pending.
- T12 (S1, S3): Serve the React build from FastAPI, retire the vanilla pages, rewrite static tests against the entrypoint. Route: inline. Status: pending.

## Log

- L1: "migremos entonces a React + TypeScript + Vite"
- L2: Created `frontend/` with Vite, TypeScript, React auth screens, and an API client preserving `/auth/login`, `/auth/register`, `/auth/me` compatibility and `itertrack_token`.
- L3: `npm run build` passed and produced `source/static/app/`; FastAPI serving remained unchanged until the dashboard migration was complete.
- L4: Added the React Leaflet dashboard with JWT session guard, organization-scoped truck polling, map markers, search, selection, status, and logout. Marker labels escaped API text before HTML insertion.
- L5: `npm run build`, `make test` (106 passed), and `make check` passed after the dashboard slice.
- L6: FastAPI served the Vite entrypoint for `/`, `/register`, and `/map`, and mounted `/assets` from the generated React build. Static tests verified the React entrypoint and a real JavaScript asset.
- L7: Final checks passed: `make test` (86 passed) and `make check`.
- L8: "pretendo pasar a react, vamos a hacer un plan, comencemos modularizando primero el html"
- L9: User decision — discard the first React attempt and restart from the vanilla HTML. Committed the staged revert as `8eb1580` (`revert(frontend): discard React migration and restore vanilla static pages`). Reason recorded: `frontend/src/App.tsx` held the entire dashboard in a single component with single-line JSX, so restarting from modularized HTML establishes the component seams before the port.
- L10: Baseline after the revert — `make check` passed and `make test` reported `106 passed`.
- L11: Pre-modularization inventory — `map.html` 1185 lines (`<style>` 11-414, markup 415-506, CDN scripts 507-509, app `<script>` 510-1167 with 40 global functions, nav IIFE 1168-1183); `login.html` 202; `register.html` 319; `map-mobile.html` 487. Design tokens duplicated across the four files, 7 `:root` blocks in `map.html` alone. No `/static` mount exists in `source/main.py`.
- L12: T4 done in `dda1f26`. Extracted verbatim, preserving cascade order: `css/map.css` (402 lines, the map page's whole block moved as-is because the file stacks successive design revisions via repeated `:root`/`.app`/`.top` overrides), `css/auth-tokens.css` (the single light/dark token block that login and register duplicated byte for byte), `css/auth.css` (shared shell/brand/form primitives), `css/login.css` (`.meta` plus login's `.status.ok`), `css/register.css` (`.mode`). `source/main.py` mounts only `/static/css`; the HTML stays behind explicit `FileResponse` routes. Page sizes: `map.html` 1185→782, `register.html` 319→231, `login.html` 202→117.
- L13: Preserved behaviour instead of silently fixing two inherited divergences: login renders `.status.ok` as `#f5f7f6` (near-white on the light form panel, effectively invisible) while register uses `#2f8f68`; and login's focus-visible selector omitted `.mode button:focus-visible`. The shared sheet carries register's green with a `login.css` override for login's current colour, so both pages render exactly as before. The near-invisible login status message is a real bug and needs an explicit decision.
- L14: `tests/test_static.py` split — page and inline-script assertions stay there, stylesheet assertions moved to `tests/test_static_css.py` reading `/static/css/*` instead of `response.text`. No coverage dropped: every literal assertion was relocated to the file that now owns it.
- L15: Verification — `make check` passed; `make test` 114 passed (was 106; +8 stylesheet tests); dev server smoke returned 200 with `text/css` for all five sheets and 200 for `/`, `/map`, `/register`.
- L16: T5 constraint found while inventorying the script — the 657-line block is 40 global functions over implicit shared mutable state (`trucks`, `markers`, `moves`, `rafId`, `selected`, filter/sort fields). ES modules cannot share module-scope state, so the first sub-step of T5 is making that state explicit in a small store module; blind file-splitting would break it.
- L17: User authorized continuing the plan: first make the current JavaScript responsibilities explicit as modules, then proceed toward React.
- L18: Extracted session/auth responsibilities into `source/static/js/session.js`, converted `map.js` to a native module, and kept the existing browser behavior and script dependency order. Static tests now recursively include local module imports when checking page behavior.
- L19: Extracted the `/trucks`, location, and history request construction into `source/static/js/truck-api.js`; response handling, polling cadence, state reuse, and telemetry updates remain unchanged in `map.js`. `make check` and `make test` pass with 114 tests.
- L20: Created `source/static/js/truck-store.js` and moved truck collection, selection, filters, marker map, movement map, and animation-frame state behind explicit accessors. Updated static assertions for the new store API; `node --check`, `make check`, and `make test` pass with 114 tests.
- L21: Extracted truck list reconciliation into `source/static/js/truck-sync.js`; it preserves existing truck objects, removes stale markers and moves, clears invalid selection, and handles authenticated API errors. `node --check`, `make check`, and `make test` pass with 114 tests.
- L22: Extracted telemetry transformations into `source/static/js/truck-telemetry.js` and filter/sort logic into `source/static/js/truck-selection.js`. Intermediate checks passed after each slice; final `node --check`, `make check`, and `make test` pass with 114 tests.
- L23: Extracted marker tweening into `source/static/js/truck-movement.js` using an injected movement controller. Updated the movement assertion and re-ran intermediate syntax/check/test gates; 114 tests pass. Rendering extraction remains pending because it is the largest coupling boundary.
- L24: Extracted charts/list rendering into `truck-charts.js` and `truck-list.js`, then marker/detail rendering into `truck-marker.js` and `truck-detail.js`. Updated static assertions for the new module-owned symbols. Final `node --check`, `make check`, and `make test` pass with 114 tests.
- L25: T6 done. Converted the sidebar-toggle IIFE in `map-nav.js` into a native ES module (`<script type="module">`, IIFE wrapper removed since module scope is already private) and closed T5. `node --check` passes for all 16 JS files; `make check` and `make test` pass with 114 tests. Browser smoke: `/`, `/map`, and `/register` return 200 and load their local assets; the nav toggle flips `.nav-off`, `aria-expanded`, `aria-label`, and `localStorage.itertrack-nav` correctly. The only console errors are the known CDN blocks (Leaflet, MapLibre, Google Fonts) in the restricted browser environment.
