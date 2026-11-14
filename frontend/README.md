# IterTrack frontend

SPA en **React 19 + TypeScript + Vite**. FastAPI la sirve desde `frontend/dist`
(ver `source/main.py`); el historial de la migración está en
`odd/tasks/react-frontend-migration.md`.

- **Rutas:** `/` (login), `/register`, `/map` (panel), `/fleet` (Camiones) y
  `/viajes` (Rutas) — React Router.
- **API client:** `src/api/` — wrappers tipados sobre `/auth`, `/config`, `/trucks`
  y viajes/destinos (`/trips`, `/chargers`, `/depots`). Contrato: `source/schemas/`,
  `source/services/`.
- **Componentes:** `src/components/` — mapa, lista de flota, buscador, detalle,
  gráficos y layout con lateral.
- **Móvil:** `src/mobile/` — layout, drawer y vistas propias hasta 640 px de ancho (`App.tsx`).
- **Lógica pura:** `src/lib/` — `truckIcon`, `movement`, `route`, `mapHandle` y
  `trucks` (`POLL_MS`, `isFresh`, `buildHistory`).
- **Estado:** `src/state/DashboardProvider.tsx` — guard de sesión contra `/auth/me`,
  polling cada 3 s y carga del historial al seleccionar un camión.
- **Estilos:** `src/styles/base.css` (sizing del root), `auth.css` (login y registro,
  scopeado a `.auth-page`), `dashboard.css` (escritorio) y `mobile.css` (móvil,
  colgado de `.m-app`). Cada hoja define sus propios tokens.

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

El dev server proxya `/auth`, `/trucks`, `/devices`, `/trips`, `/chargers`,
`/depots` y `/health` a `http://localhost:8000`, así que hay que tener la API
corriendo. `/config` no se proxya: el dev server responde un mock con la demo
encendida para que el botón «Entrar a la demo» aparezca en local.

```bash
cd frontend
npm run dev
```

## Producción

`npm run build` genera `dist/` con assets hasheados. FastAPI los monta en
`/assets` y devuelve `index.html` en `/`, `/register`, `/map`, `/fleet` y
`/viajes`; si el build no existe, esas rutas responden `503`.

`dist/` está en `.gitignore`: cualquier despliegue debe compilar el frontend
antes de levantar el servidor.

```bash
make frontend      # desde la raíz del repo: npm ci && npm run build
```
