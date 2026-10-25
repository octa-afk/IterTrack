# Progreso automático del viaje

El estado del viaje lo mueve el camión, no el operador. Cada punto aceptado por
`POST /devices/ingest` evalúa la proximidad a las paradas y al depósito.
Rama `feat/trip-progress`, base `develop`.

Test runner: `make test` (pytest, SQLite en memoria).

## Specs

- S1 — `advance_trip_progress(db, truck_id, lat, lng, measured_at)`: toma el viaje abierto (`planned`/`in_progress`) más reciente del camión; si no hay, devuelve `None`. No hace commit: la transacción es del llamador.
- S2 — Un viaje `planned` pasa a `in_progress` cuando el punto entra en el radio del depósito (`depots.radius_m`).
- S3 — Una parada `pending` pasa a `arrived` con `arrived_at = measured_at` cuando el punto entra a `STOP_RADIUS_M` (120 m).
- S4 — Una parada `arrived` pasa a `delivered` con `departed_at = measured_at` cuando el punto sale de ese radio.
- S5 — Si el viaje no tiene depósito, llegar a la primera parada también lo pone `in_progress`.
- S6 — El viaje pasa a `done` cuando **todas** las paradas están `delivered`.
- S7 — Una parada sin coordenada se saltea y mantiene el viaje abierto: no se puede confirmar una entrega en un lugar desconocido.

## Tasks

- T1 — S1: módulo `source/services/trip_progress.py` — inline.
- T2 — S2–S6: reglas de depósito, parada y cierre — inline.
- T3 — cableado en la ingesta, dentro del savepoint del punto aceptado — inline.
- T4 — 8 tests en `tests/test_trip_progress.py` — inline.

## Log

- L1 — user: "vamos con lo primero" (sobre la lista de mejoras para la demo: progreso automático del viaje).
- L2 — El radio de parada es una constante (120 m) y no una columna: un destino es una dirección, y agregar `radius_m` por parada hoy no aporta. El del depósito sí existe y se usa.
- L3 — `arrived` al entrar y `delivered` al salir, con una sola muestra por punto: no hace falta guardar estado extra, el estado de la parada ya lo es.
- L4 — Consecuencia para la demo: los viajes de `seed_demo` se completan en ~11 minutos de simulación, porque las tres paradas están en el mismo circuito que el camión recorre en ~15. Después de eso la sección Rutas muestra todo finalizado y el mapa no tiene destinos. Pendiente de decidir: renovación automática de viajes demo o reset más frecuente.
- L5 — Riesgo: 1 (cambia datos persistidos: estado de viajes y paradas). La regla es aditiva, no toca la telemetría.
