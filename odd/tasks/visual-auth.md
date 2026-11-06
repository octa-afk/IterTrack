# Feature: Visual Authentication (Fase 2 → Fase 3 bridge)

## Objective
Give IterTrack a visible, usable authentication flow in the browser: a login page backed by the existing OAuth2+JWT API, and a guard on the live map. Vanilla stack (no build tooling) by explicit decision; SPA migration is deferred with written criteria.

## Problem / Why
- The backend has full JWT auth (`/auth/register`, `/auth/login`, `/auth/me`) but nothing visual: `source/static/map.html` (515 lines vanilla JS) only calls public GET endpoints and ignores auth entirely.
- The user (junior maintainer) wants to SEE and UNDERSTAND the auth flow. Vanilla keeps the JWT mechanics visible (login → token → header → 401 handling).
- ROADMAP.md Fase 3 explicitly left the frontend stack "a definir". Decision recorded: vanilla now, SPA later under written criteria.

## Scope (authorized)
- `source/static/login.html` — NEW login page (form → `POST /auth/login`, form-encoded per `OAuth2PasswordRequestForm`; store `access_token` in `localStorage`; redirect to `/map`).
- `source/static/map.html` — auth guard: no token → redirect to `/`; validate via `GET /auth/me` with `Authorization: Bearer <token>`; attach the header to EVERY existing fetch; logout control (clear token → `/`).
- `source/main.py` — `GET /` serves `login.html`; `GET /map` keeps serving `map.html`; favicon route unchanged.
- `tests/test_static.py` — NEW smoke tests for `/` and `/map` (TDD: RED first — `GET /` currently returns the map page).
- `ROADMAP.md` — record the stack decision + SPA migration criteria (Fase 3).
- `AGENTS.md` — update static-assets section (section 4.6) for the new `/` route.

## Out of scope
- Registration UI (register stays curl/docs only for the MVP).
- Any SPA/Vite/Node tooling.
- Roles, multitenancy (ROADMAP Fase 2 remainder).
- Styling frameworks (minimal hand-written CSS only).

## Constraints
- UI copy language must match the existing map.html UI language (writer checks first).
- No token/user data via `innerHTML` (XSS) — use `textContent`.
- `scripts/selfcheck.py` must keep passing (it exercises map.html JS via node).
- No commits, no pushes (user policy: explicit request only).
- Backend behavior unchanged except the new static route.

## Acceptance criteria
- [ ] `GET /` returns the login page; submitting valid credentials lands on `/map` with the map working. (Server side observed: `GET /` 200 + login marker, form-encoded login 200 + token, `GET /map` 200; real-browser navigation pending — no browser in this environment.)
- [x] Without a valid token, `/map` redirects to `/`.
- [x] With a valid token, all existing map fetches work with the Bearer header (no 401s on public GETs either — header attached harmlessly).
- [x] 401 on `/auth/me` clears the token and returns to login.
- [x] Logout clears the token.
- [x] `make check && make test` green (including the new static tests).
- [x] `env/bin/python scripts/selfcheck.py` green.
- [x] ROADMAP.md documents the vanilla decision + migration criteria.

## Checks / verification
- TDD: `env/bin/python -m pytest tests/test_static.py -v` RED → GREEN.
- `make check && make test` (full suite).
- `env/bin/python scripts/selfcheck.py` (map JS logic via node + TestClient).
- Bounded live smoke: uvicorn on a test port + curl/httpx login flow against a test user, then shut down.

## Progress
- [x] Requirements explored (map.html structure, ROADMAP Fase 3, main.py routes).
- [x] Writer implements the scope above.
- [x] Verification observed (RED→GREEN pytest, `make check && make test` 15/15, selfcheck 17/17, live smoke 5/5 on :8017, node guard harness 11/11).
- [x] Native review (RDD) attempted with user consent: high-risk candidate frozen (7 files, 306 lines, lineage review-15809c888fc1797e), but all 4 lens relays refused with `opencode_review_transport_relay_refused (reason: provider_failed)` — KNOWN upstream defect: OpenCode free tier rejects child sessions of Gentle AI's managed read-only agents (equivalent issue Gentleman-Programming/gentle-ai#5413, open, no published fix; occurrence comment blocked: no gh/token on machine, no blind retries per contract). Exact captured decline executed once and validated; STATUS re-entry: applicability=unrelated, 0 candidates — no stale authority. Details in Engram topic `gentle-ai/review-transport-defect`.
- [ ] User browser click-through (login form → land on `/map`) — only unobserved acceptance item; server-side flow fully verified.
- [x] Commit `01d1b16 feat(auth): add vanilla login page and client-side map guard` (user requested; 7 files, +303/−11).
- [ ] Native review for the committed slice: `gentle-ai review assess --base-ref 39e6387 --committed-only` returned risk=high, review_due=true (reason high_risk). NOT retried: the lens transport is known-blocked on OpenCode free tier (issue gentle-ai#5413, see Engram topic `gentle-ai/review-transport-defect`). Reattempt only after #5413 ships a fix or the runtime leaves free tier.
- [ ] Push pending for the branch (39e6387 + 01d1b16) — push only on explicit user request.

## Next steps for the resuming session
1. Ask whether the browser click-through worked; if yes, ask to commit (conventional commit, no AI attribution, e.g. `feat(auth): add vanilla login page and client-side map guard`).
2. Do NOT retry the native review while on OpenCode free tier — same defect refuses all lens relays; check issue #5413 for a fix first.
3. Register flow from terminal (server on :8000): `curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" -d '{"username":"...","email":"...@test.com","full_name":"...","password":"..."}'` then log in via the browser form at `/`.

## Delivery
Forecast ~220 authored changed lines → single work unit, no chaining needed. Branch: `experiment/http`.
