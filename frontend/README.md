# IterTrack frontend

SPA en **React 19 + TypeScript + Vite**. FastAPI la sirve desde `frontend/dist`
(ver `source/main.py`); el historial de la migración está en
`odd/tasks/react-frontend-migration.md`.

- **Rutas:** `/` (login), `/register`, `/map` (panel) — React Router.
- **API client:** `src/api/` — wrappers tipados sobre `/auth/*` y `/trucks/*`
  (contrato: `source/schemas/`, `source/services/`).
- **Componentes:** `src/components/` — mapa, lista de flota, detalle, gráficos y tarjetas.
- **Lógica pura:** `src/lib/` — `truckIcon`, `movement`, `trucks` (`POLL_MS`, `isFresh`, `buildHistory`).
- **Estado:** `src/state/DashboardProvider.tsx` — guard de sesión contra `/auth/me`,
  polling cada 3 s y carga del historial al seleccionar un camión.
- **Estilos:** `src/styles/base.css` (sizing del root), `auth.css` (tokens y estilos scopeados a `.auth-page`)
  y `dashboard.css` (panel). Cada hoja define sus propios tokens en `:root`/`.auth-page`.

## Scripts

```bash
npm install        # install dependencies
npm run dev        # Vite dev server on :5173
npm run build      # typecheck (tsc) + production build to dist/
npm run lint       # oxlint
npm run preview    # serve the production build
```

Requiere **Node.js 22+**.

## Desarrollo

El dev server proxya `/auth`, `/trucks`, `/devices` y `/health` a
`http://localhost:8000`, así que hay que tener la API corriendo:

```bash
cd frontend
npm run dev
```

## Producción

`npm run build` genera `dist/` con assets hasheados. FastAPI los monta en
`/assets` y devuelve `index.html` en `/`, `/register` y `/map`; si el build no
existe, esas rutas responden `503`.

`dist/` está en `.gitignore`: cualquier despliegue debe compilar el frontend
antes de levantar el servidor.

```bash
make frontend      # desde la raíz del repo: npm ci && npm run build
```
