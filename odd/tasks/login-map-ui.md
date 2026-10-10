# Feature: login-map-ui

## Objective
Replace `source/static/login.html` and `source/static/map.html` with the v8 designs from `extras/ejemplos html/` (login example + dashboard-flota-v8 light/dark with a runtime theme toggle), wiring IterTrack's real auth/tracking flows.

## Why
The current static pages use the legacy look. `extras/` holds the agreed v8 design (login + fleet dashboard, light and dark variants).

## Scope
- IN: rewrite `login.html` and `map.html`; light/dark runtime toggle (persisted); wire real flows; add tests for new behavior; copy any asset served by pages from `extras/` into `source/static/`.
- OUT: `register.html` redesign (user asked only for login + map), backend changes, commits (user confirmation required), push/PR.

## Constraints
- `extras/` is gitignored and read-only (design source of truth).
- Preserve existing test hooks: `id="login-form"`, `src="/logo"`, `href="/register"` (login), `id="map"` (map).
- Real flows: `POST /auth/login` as `application/x-www-form-urlencoded` (username/password) → `access_token` → `localStorage.itertrack_token` → redirect `/map`; map guards via `GET /auth/me` with `Authorization: Bearer` (401/missing → clear storage → redirect `/`); trucks data from `GET /trucks` (org-scoped); logout button clears token; API errors rendered with `textContent` (never `innerHTML`).
- Examples call placeholder APIs (`/api/login` JSON, `/api/camiones`) — replace with the real endpoints; keep example design and Spanish copy verbatim.
- Dark variant in examples = light base + unconditional `:root{color-scheme:dark;...}` override (line ~222) → scope it for runtime toggle (e.g. `:root.dark`) and add a persisted toggle button.
- Leaflet 1.9.4 (cdnjs) + Poppins (Google Fonts) via CDN, as in the examples.

## Delivery strategy
Forecast at creation: ~1000 authored lines (login ~300, map ~650, tests ~50) → exceeds the 400-line heuristic → strategy `ask-on-risk`: ask the user for the chain strategy before the first commit of this feature; record the answer here.
- Strategy chosen: _pending_
- Slice boundaries: _pending_

## Tasks
- [x] T1 (RED): add tests asserting new behavior — map page has theme-toggle hook and dark palette; login wires `/auth/login`; map references `/auth/me` + Bearer + logout. Run `make test`, observe the new tests fail on current pages. — **evidence**: 7 tests added; RED observed: `4 failed, 38 passed` (test_login_page_uses_v8_poppins_design, test_map_page_has_theme_toggle_hook, test_map_page_has_dark_theme_palette, test_map_page_uses_example_cdn_leaflet). 3 flow tests were green on arrival (behavior pre-existed).
- [x] T2: rewrite `login.html` from the example, wire the real login flow, preserve hooks. — **evidence**: `source/static/login.html` rewritten; hooks at :120 `src="/logo"`, :123 `id="login-form"`, :142 `href="/register"`; real flow at :168-183.
- [x] T3: rewrite `map.html` from `dashboard-flota-v8` light + scoped dark override, runtime persisted toggle, wire auth guard + `/trucks` + logout. — **evidence**: `source/static/map.html` rewritten; `:root.dark` :260-332, early theme script :334-344, guard :449-467, `/trucks` Bearer :782, logout :881, `id="map"` :382.
- [x] T4: copy any asset the served pages reference from `extras/` into `source/static/`. — **evidence**: nothing to copy — pages use CDN + `/logo` endpoint + inline SVG; `extras/` untouched (verified `git check-ignore extras` → `.gitignore:25`).
- [x] T5: `make check && make test` all green; record results. — **evidence**: writer `make test` → `42 passed, 1 warning in 10.06s`; parent spot-check re-ran `make test` → `42 passed`; independent verifier re-ran both → green.

## Acceptance criteria
- [x] `/` and `/map` render the new designs (visual match to examples) — verifier text-diff: visible copy differs from examples only by "Correo electrónico"→"Usuario" (login) and "+Modo oscuro" (map toggle); all structural ids present.
- [x] Login flow end-to-end against the real API (form-urlencoded → token → `/map`)
- [x] Map guards with `/auth/me`, loads org-scoped trucks, logout works
- [x] Theme toggle switches light/dark at runtime and persists across reloads
- [x] `make check && make test` green (35+ tests) — **42 passed**
- [ ] No commits without explicit user confirmation — **pending user decision**

## Route declaration
- T1–T5: **delegated** (writer) — trigger: 2+ non-trivial files + reading that prepares the write.
- Verification: **delegated** (independent read-only verifier) — RDD off + native tier medium + small-model bias → tier high → writer self-verification + independent verifier. Verdict: PASS, 0 defects. Parent spot-check: `make test` → 42 passed.
- Native assessment: RDD **off** (clone-local) → no review ceremony; `gentle-ai review assess` recorded `risk: medium` (executable_change: source/static/login.html), 3 paths / 1864 changed lines, `review_due_reason: slice_budget_reached` (informational while RDD off).

## Progress
- 2026-10-10: feature created; question resolved: user chose "both themes with toggle" (not a single fixed variant).
- 2026-10-10: T1–T5 complete and verified (42/42 tests). Writer deviations disclosed and confirmed as-stated by verifier: (a) login label "Usuario" instead of "Correo electrónico" (API authenticates by username), (b) extra `<img src="/logo">` for the test hook, (c) fuel/driver/route shown as "—" (no API), (d) forgot-password + remember-session decorative, (e) logout clears the persisted theme too, (f) dark block uses the dark file's final effective values. Login page has no toggle button (faithful to its example — it only handles `prefers-color-scheme`).
- Next: user decision on commit shape (delivery strategy) — feature exceeds the 400-line heuristic (+1132/−732 authored).
