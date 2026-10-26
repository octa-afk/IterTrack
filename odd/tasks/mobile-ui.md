# Mobile UI (extras/mobile/itertrack)

Objetivo: implementar el diseño de `extras/mobile/itertrack` como interfaz móvil de la SPA, con datos reales de la API. Branch `feat/mobile-ui`. Entrega: un commit coherente en la branch (≈1.750 líneas autoradas, la mayoría el CSS portado del diseño; no se parte en slices artificiales porque el shell, el CSS y las tres pantallas forman una sola unidad). Runner: `npm --prefix frontend run build` + `npm --prefix frontend run lint` + `make check` + `make test`.

## Specs

- **S1** — Crear una branch nueva e implementar ahí el diseño de `extras/mobile/itertrack`.
- **S2** — El diseño nuevo se usa **sólo en móvil**; el dashboard de escritorio se conserva sin cambios visuales. El corte es el breakpoint existente de teléfono: `max-width: 640px` (el test `test_mobile_layout_only_below_phone_widths` exige 640/641 y rechaza 943/944 px).
- **S3** — Pantalla Panel (`/map`): mapa real Leaflet/MapLibre con el marcador de cada camión, buscador flotante (filtra la flota), botón de menú, botón de ubicación y hoja inferior con el camión seleccionado (patente, estado, último reporte, velocidad) y acceso a "Ver flota". **Sin botones de zoom**: en un teléfono el gesto de pinza y el doble toque son el control natural (L12).
- **S4** — Drawer: marca IterTrack, navegación Panel / Camiones / Rutas, Reportes y Ajustes deshabilitados ("Próximamente"), contador de alertas que filtra la flota por alerta, e identidad del usuario con "Salir".
- **S5** — Pantalla Camiones (`/fleet`): chips de filtro por estado (Todos / En movimiento / Detenidos / Apagados), orden por patente, tarjetas con patente, estado, velocidad, último reporte y rumbo; estado vacío cuando no hay coincidencias.
- **S6** — Detalle del camión (`/fleet?truck=<id>`): velocidad, combustible, chofer y rumbo, próxima parada (distancia y tiempo con `useNextStop`), gráfico de velocidad reciente, y "Ver en el mapa".
- **S7** — Pantalla Rutas (`/viajes`): viajes reales ordenados como los devuelve la API, con dador de carga, patente, salida, cantidad de destinos y "Ver recorrido" (selecciona el camión, enciende su recorrido y navega al mapa). Aviso de solo lectura para `member`.
- **S8** — Integración de datos: camiones y posiciones (`/trucks`, `/trucks/{id}/location`, `/trucks/{id}/iter`), viajes y dadores (`/trips`, `/chargers`), sesión (`/auth/me`). No se usa `IT.data` ni datos de ejemplo del diseño.
- **S9** — Sin rutas nuevas en el backend: los screens usan `/map`, `/fleet` y `/viajes`; el detalle del camión se resuelve con el query param `?truck=<id>` porque FastAPI sólo sirve la SPA en las rutas existentes.
- **S10** — El mapa se monta una sola vez en el layout móvil y se oculta (no se desmonta) al cambiar de sección, igual que en escritorio, para no recrear Leaflet/MapLibre ni volver a pedir el estilo.

## Tasks

- [x] T1 — Andamiaje móvil: hook de media query, tokens/estilos `mobile.css` con prefijo `--m-` y clases `m-`, iconos, `MobileLayout` con el mapa persistente. (S1, S2, S10) — commit `feat(movil)`; 640 px → móvil, 641 px → escritorio verificado con Playwright.
- [x] T2 — Mapa: `onReady` / `showZoomControl` en `MapView`, buscador flotante, controles de zoom/ubicación y hoja inferior. (S3) — buscador "ABC" deja 1 camión; zoom y ubicación llaman a la instancia de Leaflet.
- [x] T3 — Drawer con navegación, alertas y salir. (S4) — navegación por links probada de Panel a Rutas; drawer `inert` cuando está cerrado.
- [x] T4 — Camiones: lista con filtros y detalle con próximas paradas y sparkline. (S5, S6) — detalle muestra "2,4 km · 7 min" y el `Sparkline` con historial real.
- [x] T5 — Rutas: viajes reales, recorrido y aviso de solo lectura. (S7, S8, S9) — "Ver recorrido" navega a `/map` con la patente en la hoja inferior; `member` ve el aviso.
- [x] T6 — Verificación: build + lint + `make check` + `make test` (269 tests) y regresión de CSS nueva. (S2)

## Log

- **L1** — «quiero que crees una nueva branch e implementes el diseño que se encuentra en extras/mobile/itertrack. por supuesto integrala con los datos que ya tenemos.»
- **L2** — Decisión del humano: «Sólo móvil, conservar escritorio». Se mantiene el dashboard actual para pantallas anchas y el diseño nuevo aparece sólo por debajo del ancho de teléfono.
- **L3** — Exploración: el diseño es vanilla JS con `IT.data` de ejemplo; los datos reales viven en `DashboardContext` (`TruckState`, `visibleTrucks`, `selectedTruck`, `recorridoId`), `useNextStop` y la API de viajes. El mapa real es `MapView` y ya se monta una vez en el layout de escritorio.
- **L4** — El test `tests/test_static_css.py::test_mobile_layout_only_below_phone_widths` fija el breakpoint de teléfono en 640 px; se reutiliza para que la UI nueva no aparezca en una ventana de PC angostada. `dashboard.css` no se toca, así que las regresiones de CSS existentes siguen valiendo.
- **L5** — Riesgo de colisión de estilos: el diseño reusa `.card`, `.app`, `.nav`, `.count`, `.avatar`, etc. Por eso `mobile.css` scopea todo bajo `.m-app` y usa tokens `--m-*`.
- **L6** — Defecto encontrado en la verificación visual: el reset `.m-app button { background:none }` (0,1,1) le ganaba a `.m-card` (0,1,0) y dejaba tarjetas y chips sin fondo. Se cambió por `.m-app :where(button)` (especificidad 0).
- **L7** — Defecto de carrera: el detalle llamaba a `select(id)` antes del primer refresh del provider; `setTrucks` mapeaba sobre una flota vacía y descartaba el historial (sin sparkline). Ahora espera `ready`.
- **L8** — Defecto de Leaflet: al entrar al panel con el mapa recién mostrado tras estar `display:none`, `flyTo` proyectaba NaN y tumbaba la app (`Invalid LatLng`). Se agregaron guardas de coordenadas/zoom/tamaño en `MapView` y un `invalidateSize` + encuadre al montar `MobileMapPage`.
- **L9** — `vite.config.ts` no proxeaba `/trips`, `/chargers` ni `/depots`: la sección Rutas fallaba en desarrollo aunque el dashboard existente ya la usaba. Se agregaron al proxy de desarrollo.
- **L10** — Limitación conocida: el diseño de Rutas no incluye el formulario de alta, así que en móvil un `org_admin` no puede crear viajes (sí en escritorio, que sigue disponible). Queda para una tarea de diseño aparte.
- **L11** — Verificación: `npm run build`, `npm run lint`, `make check` y `make test` (269 pasan). Playwright con datos mockeados: 390/640 px → `.m-app`; 641/1280 px → dashboard; sin errores de consola ni `pageerror`.
- **L12** — Corrección del humano: «quitemos los botones de hacer zoom in y zoom out, al ser mobile lo mas natural es usar los gestos». Se quitó la píldora `.m-zoom` de `MobileMapPage` y su CSS; queda sólo "Mi ubicación". `showZoomControl={false}` sólo oculta los botones de Leaflet: pinch y doble toque siguen activos. Verificado con Playwright: el único botón del mapa es "Mi ubicación" y no hay errores.
- **L13** — Corrección del humano: «se superponen, corregilo. no te limites solo a moverlo, calcula de acuerdo al panel de debajo, para que funcione en cualquier dispositivo». Se reemplazó el `bottom: 200px` por un stack `.m-map-bottom` anclado abajo que contiene controles y hoja: el botón queda 10 px arriba de la hoja y se recalcula con la altura real del contenido, el safe-area y cualquier ancho. Medido en 320/360/390/430 px de ancho: separación constante de 10 px, sin solape. El subtítulo de la hoja envuelve en unidades ("hace 3 s" no se parte).
- **L14** — Corrección del humano: «ese mismo boton hacelo celeste, no uses playwirgth, limitate solo a copiar el color celeste de algun celeste que se use ya dentro de la pagina». El botón de ubicación usa `--m-accent-soft` (`#e1e7fb`), el mismo celeste de la tarjeta seleccionada; el icono va en `--m-accent-ink`. No afecta a los demás `.m-btn-round` (menú).
