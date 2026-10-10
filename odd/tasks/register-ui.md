# Feature: Registration UI (register entry point + page)

## Objective
Let a user create an account from the browser: a "Registrate" entry point on the login
page and a `register.html` page that posts to the existing `POST /auth/register`, then
lands on `/map`.

## Problem / Why
- `POST /auth/register` exists and is public (`source/services/auth.py:62`), but there is
  no UI: registration is curl/docs only. It was explicitly listed as out of scope in
  `odd/tasks/visual-auth.md` ("Registration UI (register stays curl/docs only for the MVP)").
- User request (2026-10-10): "implementar un botón de registro en la pantalla de login".

## Scope (authorized)
- `source/static/register.html` — NEW page. Form: usuario, email, nombre completo,
  contraseña. Client-side JS: `POST /auth/register` with JSON body; on `201` auto-login via
  `POST /auth/login` (`application/x-www-form-urlencoded`, per `OAuth2PasswordRequestForm`),
  store `access_token` under `itertrack_token`, redirect to `/map`; on `400` show the API
  `detail` message. Link back to `/`.
- `source/static/login.html` — visible entry point (link/button) to `/register`.
- `source/main.py` — new `GET /register` route returning
  `FileResponse("source/static/register.html")` (same pattern as `/` and `/map`).
- `tests/test_static.py` — coverage for `GET /register` and for the login page linking to it.
- `AGENTS.md` — section 4 (static assets) lists the served routes; keep it accurate.

## Out of scope
- Any backend/auth change: `/auth/register`, `/auth/login`, `/auth/me` stay untouched.
- Email verification, password-strength rules, captcha, rate limiting, roles/approval flow.
  Open self-registration keeps behaving exactly as the endpoint already does.
- SPA/Vite/Node tooling and styling frameworks (vanilla + hand-written CSS only).

## Constraints
- UI copy in Spanish (neutral), matching the existing `login.html` / `map.html` tone.
- Never render server messages with `innerHTML` — use `textContent` (XSS).
- Vanilla JS only, no build step; keep `scripts/selfcheck.py`, `make check`, `make test` green.
- No commits, no pushes (user policy: explicit request only).
- `source/static/login.html` already carries an uncommitted user tweak (logo size) —
  preserve it, do not revert.

## Acceptance criteria
- [x] `GET /register` returns 200 with the register form marker (was 404 — RED evidence: 404).
- [x] Login page shows a visible link to `/register` (`href="/register"` asserted by test).
- [x] New-account flow works end to end server-side: `POST /auth/register` 201 →
      `POST /auth/login` 200 + token → account usable (`tests/test_auth.py` + selfcheck API checks).
- [ ] Duplicate username / duplicate email rendered in the page — backend 400 + `detail` read via
      `textContent` is implemented and tested server-side; browser rendering still unobserved
      (covered by the click-through item below).
- [x] `make check && make test` green (19 tests: 17 pre-existing + 2 new).
- [x] `env/bin/python scripts/selfcheck.py` green (17/17).

## Checks / verification
- TDD: RED first — a `GET /register` test in `tests/test_static.py` fails (404) before the route exists.
- `make check && make test`
- `env/bin/python scripts/selfcheck.py`

## Progress
- [x] Exploration: routes in `source/main.py`, `login.html`, `source/services/auth.py`,
      `tests/test_static.py`, `scripts/selfcheck.py` (only reads `map.html`, unaffected).
- [x] Writer implements the scope above (delegated direct, one writer).
- [x] Verification observed:
      - RED before impl: `pytest tests/test_static.py` → 2 failed (404 on `/register`), 4 passed.
      - GREEN after impl: `pytest tests/test_static.py` → 6 passed.
      - `make check && make test` → 19 passed (reproduced by the parent as spot check).
      - `env/bin/python scripts/selfcheck.py` → 17/17.
- [x] Native review (RDD): consent granted by the user (medium risk, 6 files / 299 lines,
      1 selected lens `review-reliability`, correction budget 150). BLOCKED at collect:
      `opencode_review_transport_relay_refused (reason: provider_failed)` on the provider-issued
      lens task — same runtime defect recorded in visual-auth (free tier refuses Gentle AI's
      managed read-only subagents). Contract followed: exact-lineage STATUS re-offered the same
      slot (no blind retry), then `review capture-unachievable --reason provider_relay_refused`
      with the exact binding → `recorded: true`; STATUS now `stop/unachievable_lens_slot`.
      Reversible via the returned `--withdraw=true` command. NO receipt, NO approval: delivery
      stays a human decision under ordinary repository policy.
- [x] User decision: receipt-driven development disabled clone-local (`clone-local: off`,
      `global: on`) via `gentle-ai review mode disable --scope clone --cwd /home/octa/IterTrack`,
      because every medium/high candidate dead-ends on this runtime. Re-enable with
      `gentle-ai review mode enable --scope clone` once the lens relay works.
- [ ] User browser click-through (register → land on `/map`).
- [x] Work-unit commits on `experiment/http` (user requested the commit):
      - `b51430d style(auth): resize login logo mark` — the user's own uncommitted logo tweak,
        split into its own unit so the feature commit stays independently revertable.
      - `d3e8c57 feat(auth): add browser registration flow` — page, route, link, tests and docs.
      - Post-restore re-verification: `make check && make test` 19 passed, selfcheck 17/17.

## Route declaration
- Writer task: delegated direct (trigger: 2+ files across page + route + tests).
- Exploration: parent inline (one bounded batch, <3 calls per step).

## Delivery
- Single work unit, no chaining: `d3e8c57` (6 files, +315/−1) plus the separate 3-line logo unit
  `b51430d`. Branch `experiment/http`, 2 commits ahead of `origin/experiment/http`; push only on
  explicit user request.
- Review state for this slice: receipt-driven development disabled clone-local by user decision,
  so delivery is `disabled/unmanaged` under ordinary repository policy — no receipt, no approval.
