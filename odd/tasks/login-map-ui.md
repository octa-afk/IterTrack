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
- Preserve test hooks: `id="login-form"`, `href="/register"` (login), `id="map"` (map). The original `src="/logo"` hook was removed on 2026-10-10 with the total Itertrack_logo.png removal (user request); it is no longer a required hook.
- Real flows: `POST /auth/login` as `application/x-www-form-urlencoded` (username/password) → `access_token` → `localStorage.itertrack_token` → redirect `/map`; map guards via `GET /auth/me` with `Authorization: Bearer` (401/missing → clear storage → redirect `/`); trucks data from `GET /trucks` (org-scoped); logout button clears token; API errors rendered with `textContent` (never `innerHTML`).
- Examples call placeholder APIs (`/api/login` JSON, `/api/camiones`) — replace with the real endpoints; keep example design and Spanish copy verbatim.
- Dark variant in examples = light base + unconditional `:root{color-scheme:dark;...}` override (line ~222) → scope it for runtime toggle (e.g. `:root.dark`) and add a persisted toggle button.
- Leaflet 1.9.4 (cdnjs) + Poppins (Google Fonts) via CDN, as in the examples.

## Delivery strategy
Forecast at creation: ~1000 authored lines (login ~300, map ~650, tests ~50) → exceeds the 400-line heuristic → strategy `ask-on-risk`: ask the user for the chain strategy before the first commit of this feature; record the answer here.
- Strategy chosen: **single commit** (user choice, 2026-10-10) — one coherent feature commit on `experiment/http`; tests cover both pages, so review keeps them together.
- Slice boundaries: single slice — commit `f3bb9dd` (`feat: redesign login and map pages with v8 UI`), 9 files, +1180/−759 (amended 2026-10-10 to fold in the total Itertrack_logo.png removal; supersedes `a2ac400`).

## Corrections (user review round, 2026-10-10)
- [x] C1: Scale the whole UI of `login.html` + `map.html` by **15%** (user asked "10–20% más grande" → midpoint). Method: multiply px literals ×1.15 in `<style>`, `style="..."` attributes, JS px literals and media-query breakpoints. Safety rules: keep hairlines ≤1.5px unchanged; do NOT touch `%`, `vh`/`dvh`, colors, unitless values (`stroke-width`, `line-height`, z-index), or SVG path data. Rounding: original ≤1.5px → unchanged; result ≥10 → integer; else 1 decimal. CSS `zoom` is explicitly rejected (breaks Leaflet coordinate math on ancestors of `#map`). `register.html` untouched (legacy, out of scope). RED-first: new test pinning the scaled base font sizes + breakpoints. — **evidence (2026-10-10)**: RED `1 failed, 40 passed` (`test_pages_use_scaled_ui_scale`) → GREEN `41 passed` (writer, parent spot-check, independent verifier agree). Scaled: login 88/94 px tokens (6 hairlines/.2px kept), map 255/291 (36 kept) + 3 JS px constants coupled to CSS geometry (`129 - 18`, limit `18`, `Math.max(3.5,…)`, `'14px'`). Orchestrator fixed the Leaflet divIcon coupling the writer flagged: `iconSize:[39,39]`, `iconAnchor:[19.5,19.5]` ↔ `.pin` 39px. Breakpoints: 860→989, 480→552, 1100→1265, 820→943, 821→944. Verifier: PASS, 0 defects, 8 px-pair spot checks ✅. Native assess: `unassessable` (untracked inventory changed) → treated high → writer self-verification + independent verifier. Committed as `622a162` `fix: scale login and map ui by 15 percent` (3 files, +188/−173); review round continues (C2… pending).
- [ ] **C2 — scheduled for next session (2026-10-11)**: redesign the truck marker inside the map and its route rendering — user's exact words: "corregir el diseño del camión dentro del mapa y su recorrido". Expected scope: the truck pin visual design (`divIcon` / `.pin` in `source/static/map.html`) and how the truck's route/trajectory is drawn (history polyline from `GET /trucks/{id}/iter`). **Specific requirements must be confirmed with the user at session start — do not assume the desired look.**
- [ ] C3…Cn: pending — user is mid review round.

## Tasks
- [x] T1 (RED): add tests asserting new behavior — map page has theme-toggle hook and dark palette; login wires `/auth/login`; map references `/auth/me` + Bearer + logout. Run `make test`, observe the new tests fail on current pages. — **evidence**: 7 tests added; RED observed: `4 failed, 38 passed` (test_login_page_uses_v8_poppins_design, test_map_page_has_theme_toggle_hook, test_map_page_has_dark_theme_palette, test_map_page_uses_example_cdn_leaflet). 3 flow tests were green on arrival (behavior pre-existed).
- [x] T2: rewrite `login.html` from the example, wire the real login flow, preserve hooks. — **evidence**: `source/static/login.html` rewritten; hooks at :119 `id="login-form"`, :138 `href="/register"`; real flow at :161-180 (positions after the 2026-10-10 logo removal; the forced `src="/logo"` img was removed by user request).
- [x] T3: rewrite `map.html` from `dashboard-flota-v8` light + scoped dark override, runtime persisted toggle, wire auth guard + `/trucks` + logout. — **evidence**: `source/static/map.html` rewritten; `:root.dark` :260-332, early theme script :334-344, guard :449-467, `/trucks` Bearer :782, logout :881, `id="map"` :382.
- [x] T4: copy any asset the served pages reference from `extras/` into `source/static/`. — **evidence**: nothing to copy — pages use CDN + `/logo` endpoint + inline SVG; `extras/` untouched (verified `git check-ignore extras` → `.gitignore:25`).
- [x] T5: `make check && make test` all green; record results. — **evidence**: writer `make test` → `42 passed, 1 warning in 10.06s`; parent spot-check re-ran `make test` → `42 passed`; independent verifier re-ran both → green.

## Acceptance criteria
- [x] `/` and `/map` render the new designs (visual match to examples) — verifier text-diff: visible copy differs from examples only by "Correo electrónico"→"Usuario" (login) and "+Modo oscuro" (map toggle); all structural ids present.
- [x] Login flow end-to-end against the real API (form-urlencoded → token → `/map`)
- [x] Map guards with `/auth/me`, loads org-scoped trucks, logout works
- [x] Theme toggle switches light/dark at runtime and persists across reloads
- [x] `make check && make test` green (35+ tests) — **42 passed** at feature completion; **40 passed** after the logo removal (the 2 logo tests were deleted with the endpoint they covered)
- [x] No commits without explicit user confirmation — user confirmed the commit shape (single commit) before committing.

## Route declaration
- T1–T5: **delegated** (writer) — trigger: 2+ non-trivial files + reading that prepares the write.
- Verification: **delegated** (independent read-only verifier) — RDD off + native tier medium + small-model bias → tier high → writer self-verification + independent verifier. Verdict: PASS, 0 defects. Parent spot-check: `make test` → 42 passed.
- Native assessment: RDD **off** (clone-local) → no review ceremony; `gentle-ai review assess` recorded `risk: medium` (executable_change: source/static/login.html), 3 paths / 1864 changed lines, `review_due_reason: slice_budget_reached` (informational while RDD off).

## Progress
- 2026-10-10: feature created; question resolved: user chose "both themes with toggle" (not a single fixed variant).
- 2026-10-10: T1–T5 complete and verified (42/42 tests). Writer deviations disclosed and confirmed as-stated by verifier: (a) login label "Usuario" instead of "Correo electrónico" (API authenticates by username), (b) extra `<img src="/logo">` for the test hook, (c) fuel/driver/route shown as "—" (no API), (d) forgot-password + remember-session decorative, (e) logout clears the persisted theme too, (f) dark block uses the dark file's final effective values. Login page has no toggle button (faithful to its example — it only handles `prefers-color-scheme`).
- Next: user decision on commit shape (delivery strategy) — feature exceeds the 400-line heuristic (+1132/−732 authored).
- 2026-10-10: user chose **single commit**. Initial work-unit commit `a2ac400` `feat: redesign login and map pages with v8 UI` on `experiment/http` (4 files, +1181/−732).
- 2026-10-10: user requested **total removal of Itertrack_logo.png before committing** (scope confirmed: repo-wide). Removed: the PNG file, the `GET /logo` endpoint (`source/main.py`), the `<img src="/logo">` from login.html and register.html, dead `.brand-logo` / `.login-card .logo` CSS, both logo tests (`test_logo_serves_image`, `test_login_page_references_logo`), and the README/AGENTS rows (README favicon row corrected to `isologo.png` as well). Verified: `make check` exit 0, `make test` → **40 passed**. Feature commit amended (local-only history) → **`f3bb9dd`** (9 files, +1180/−759). Push still pending user decision. Record commit: `docs(odd): record login-map-ui work-unit commit`.
- 2026-10-10: correction round state at session pause: C1 committed (`622a162` `fix: scale login and map ui by 15 percent` + `664d35a` docs record). **Next session (2026-10-11): correction C2 — redesign the truck marker inside the map and its route rendering** (details pending user confirmation). Push to `origin/experiment/http` still pending (4+ local commits).
