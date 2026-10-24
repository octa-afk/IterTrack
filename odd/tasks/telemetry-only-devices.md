# Telemetría solo por dispositivo

Rama `develop`. Backend FastAPI + simulador + frontend. Verificación: `make check`, `make test`, `npm --prefix frontend run lint && npm --prefix frontend run build`.

## Specs

- **S1 — Sin escritura humana de ubicaciones.** `PUT /trucks/{id}/location` deja de existir. Ningún endpoint autenticado con JWT de usuario agrega puntos de tracking: el único camino de escritura de telemetría es `POST /devices/ingest`, con token de dispositivo, asignación abierta y camión activo.
- **S2 — Alta de camión sin punto inicial.** `POST /trucks` y `POST /organizations/{id}/trucks` reciben solo `{"id": <int>, "plate": "<str>"}` y crean el camión sin insertar un `TrackingPoint`. Un camión recién creado responde `404` en `GET /trucks/{id}/location` hasta que su dispositivo reporte.
- **S3 — El simulador deja el modo usuario.** `scripts/simulate_trucks.py` emite únicamente por `POST /devices/ingest`; desaparecen `--mode`, `actualizar_ubicacion`, el login de telemetría (`API_USER`/`API_PASSWORD`) y la renovación de JWT humano (`refresh_headers`).
- **S4 — El seed no inyecta posiciones.** `scripts/seed_demo.py` crea camiones y dispositivos, no puntos de tracking.
- **S5 — Sin código muerto en el cliente.** `frontend/src/api/trucks.ts` deja de exportar `updateLocation` y el tipo `Location` que solo usaba esa función.

## Alcance no incluido

- `DELETE /trucks/{id}/iter` sigue siendo de `org_admin`: es limpieza administrativa, no telemetría.
- `PATCH /trucks/{id}/activate` y el resto de la administración no cambian.
- El camino del hardware (`/devices/ingest`) no se toca.

## Tasks

| ID | Specs | Route | Estado |
|---|---|---|---|
| T1 | S1, S2, S4 | inline | hecho |
| T2 | S3 | inline | hecho |
| T3 | S5 | inline | hecho |
| T4 | docs | inline | hecho |

## Log

**L1 (2026-10-24).** «saca el put y el punto humano, que solo la esp32 mande ubicaciones».

**L2 — motivo.** `PUT /trucks/{id}/location` es de la Fase 1, cuando no había hardware y una cuenta empujaba puntos. Al llegar la autenticación por dispositivo quedó vivo con la única guarda de `get_current_user`: cualquier `member` podía inyectar posiciones falsas. `POST /trucks` hacía lo mismo con un punto inicial al dar de alta el camión.

**L3 — backend.** `_persist_truck` ya no inserta un `TrackingPoint`; `POST /trucks` y `POST /organizations/{id}/trucks` reciben el modelo plano (`{"id", "plate"}`) y solo crean el camión. Se retiró el endpoint `PUT /{truck_id}/location` y, con él, `schemas.Location` y `schemas.TrackingPoint`, que quedaban sin consumidores. El 409 por camión inactivo sigue existiendo, pero ahora solo en la ingesta por dispositivo (ya estaba cubierto por `test_assignment_is_resolved_by_recorded_at_and_inactive_truck_rejected`).

**L4 — simulador.** Se eliminó `--mode`, `actualizar_ubicacion`, el login de telemetría (`API_USER`/`API_PASSWORD`) y la renovación de JWT humano (`refresh_headers`). `simular_ruta` exige un `sender` de dispositivo y falla con `ValueError` si falta: no hay camino alternativo. El modo `user` era el default, así que `make simulation` y el worker del compose ahora emiten siempre por `/devices/ingest`.

**L5 — tests.** Los tests del PUT se retiraron porque sus comportamientos (validación de rangos, normalización de `recorded_at` y `heading`, 409 por camión inactivo) ya están cubiertos por `tests/test_device_ingest.py` contra el schema del dispositivo, que es más estricto (`extra="forbid"`, `sequence`). Se agregaron `test_users_cannot_push_locations` (405), `test_new_truck_has_no_location_until_its_device_reports` y `test_simular_ruta_requires_a_device_sender`.

**L6 — verificación de contrato.** Contra un backend real: alta plana → `200`; `GET /trucks/99/location` inmediato → `404`; `PUT /trucks/99/location` → `405`; aprovisionar dispositivo → `201`; `POST /devices/ingest` → `accepted`; `GET /trucks/99/location` → `200`. 194 tests, ruff y mypy limpios; `npm run lint` y `npm run build` OK.

