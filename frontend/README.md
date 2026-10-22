# IterTrack frontend

React + TypeScript + Vite port of the vanilla dashboard (see `odd/tasks/react-frontend-migration.md`).

- **Routes:** `/` (login), `/register`, `/map` (dashboard) — mirror the FastAPI static routes.
- **API client:** `src/api/` — typed wrappers over `/auth/*` and `/trucks/*` (contract: `source/schemas/`, `source/services/`).
- **Tokens:** `src/styles/tokens.css` — ported from `source/static/css/auth-tokens.css`.

## Scripts

```bash
npm install        # install dependencies
npm run dev        # Vite dev server
npm run build      # typecheck (tsc) + production build to dist/
npm run lint       # oxlint
npm run preview    # serve the production build
```

The app is served by FastAPI only from T12 onward; until then it runs standalone
via `npm run dev`.
