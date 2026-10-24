# Fase 3 — estado del camión y recorrido reciente

Rama `develop`. Frontend React (`frontend/`). Verificación: `npm --prefix frontend run lint`, `npm --prefix frontend run build` (tsc) y `make test`.

## Specs

- **S1 — Estado activo/inactivo.** El listado de flota y el panel de detalle muestran `Inactivo` para un camión con `active = false`: punto gris en la lista, etiqueta `INACTIVO` junto a la patente y `Inactivo` en lugar del estado de telemetría. El marcador del mapa se atenúa (escala de grises). `GET /trucks` ya devuelve `active`; no se modifica el backend.
- **S2 — Recorrido reciente.** Al seleccionar un camión se pide `GET /trucks/{id}/iter?limit=500` y se dibuja su recorrido como polilínea del color del camión debajo de los marcadores. El panel de detalle muestra km recorridos, duración y cantidad de puntos del recorrido. Cada poll de `/location` extiende la polilínea del camión seleccionado.
- **S3 — Camión inactivo sin recorrido.** Si el camión no tiene al menos dos puntos, el panel dice `Sin recorrido suficiente todavía.`; si además está inactivo, `Camión inactivo: no recibe nuevas posiciones.` y no se dibuja polilínea.

## Tasks

| ID | Specs | Route | Estado |
|---|---|---|---|
| T1 | S1 | inline | hecho — `api/types.ts`, `lib/trucks.ts`, `components/FleetList.tsx`, `components/TruckDetail.tsx`, `lib/truckIcon.ts`, `styles/dashboard.css` |
| T2 | S2, S3 | inline | hecho — `lib/trucks.ts` (`buildPath`, `appendPath`, `tripSummary`), `state/DashboardProvider.tsx`, `components/MapView.tsx`, `components/TruckDetail.tsx` |

## Log

**L1 (2026-10-24).** «continuemos con la fase 3». Fase 3 del ROADMAP: mostrar el estado activo/inactivo del camión en la UI e historial de viajes por camión.

**L2 — decisión de producto.** El modelo no tiene "viajes" segmentados, solo puntos. Se preguntó la forma del historial y se eligió «recorrido en el mapa + resumen».

**L3 — helpers puros.** `buildPath` ordena cronológicamente los puntos de `/iter` y descarta posiciones consecutivas idénticas (un camión detenido repite coordenadas). `appendPath` agrega el punto nuevo de cada poll solo si su `recorded_at` es posterior al último, tocando el límite de 500. `tripSummary` suma distancias con `haversineM` y calcula la duración entre el primer y el último `recorded_at`.

**L4 — verificación.** `npm run lint` limpio y `npm run build` (tsc + vite) OK. Sonda funcional contra la API real: 26 puntos de `/iter` → 25 de recorrido (uno deduplicado), 0,947 km en 0,99 min, cronológico; un punto viejo no extiende la travesía y uno nuevo sí. Verificado en Chrome headless (CDP) con la app servida por Vite y el backend local: la polilínea aparece en `.leaflet-overlay-pane`, el detalle muestra `1,5 km / 2 min / 30 puntos` y el camión desactivado muestra la etiqueta `INACTIVO`.

**Hallazgo fuera de alcance.** El simulador reporta 55 km/h pero recorre ~100 m cada 3,1 s (≈117 km/h reales), así que el panel calcula la velocidad desde las coordenadas y marca `Alerta` en un camión que debería ir a 55. La velocidad del panel se deriva del desplazamiento real, no del campo `speed`, así que el dato que miente es el del simulador. No se tocó en esta fase.
