# React frontend migration
Branch: feat/telemetry-contract-hardening
Delivery: incremental work-unit commits
Test runner: npm run build; make test && make check

## Specs

1. **S1** — “migremos entonces a React + TypeScript + Vite”
   - Preserve the existing FastAPI API, JWT key, routes, organization isolation, and current frontend behavior while migrating incrementally.
   - Checks: frontend production build; `make test`; `make check`.

## Tasks

- T1 (S1): Scaffold React + TypeScript + Vite and migrate login/register flows. Route: inline. Status: complete. Commit: 39e9b48.
- T2 (S1): Migrate the authenticated map dashboard and Leaflet integration. Route: inline. Status: complete. Commit: a9bdd67.
- T3 (S1): Switch FastAPI static serving to the React build and update regression tests/docs. Route: inline. Status: complete. Commit: 62b7ae7.

## Log

- L1: migremos entonces a React + TypeScript + Vite
- L2: Created `frontend/` with Vite, TypeScript, React auth screens, and an API client preserving `/auth/login`, `/auth/register`, `/auth/me` compatibility and `itertrack_token`.
- L3: `npm run build` passed and produced `source/static/app/`; FastAPI serving remains unchanged until the dashboard migration is complete.
- L4: Added the React Leaflet dashboard with JWT session guard, organization-scoped truck polling, map markers, search, selection, status, and logout. Marker labels escape API text before HTML insertion.
- L5: `npm run build`, `make test` (106 passed), and `make check` passed after the dashboard slice.
- L6: FastAPI now serves the Vite entrypoint for `/`, `/register`, and `/map`, and mounts `/assets` from the generated React build. Static tests now verify the React entrypoint and a real JavaScript asset.
- L7: Final checks passed: `make test` (86 passed) and `make check`.
