# Alertas de ingesta agrupadas

Los puntos rechazados por `POST /devices/ingest` se guardaban en
`rejected_ingest_points` y nadie los miraba. Ahora se agrupan en una alerta por
equipo y tipo de problema. Rama `feat/ingest-alerts-v2` desde `develop`.

Test runner: `make test` (pytest, SQLite en memoria vía `conftest`).

## Specs

- S1 — `Alert`: `id`, `organization_id` (FK → organizations, nullable), `device_id` (FK → devices), `problem_type` (el `reason` del rechazo), `status` (`open`|`closed`, default `open`, con `CHECK`), `previous_alert_id` (self-FK, nullable), `created_at`, `closed_at`, `latest_occurrence_at`.
- S2 — `AlertOccurrence`: `id`, `alert_id` (FK → alerts), `rejected_point_id` (FK → rejected_ingest_points), `occurred_at`. Es la evidencia de cada ocurrencia.
- S3 — Migración `c1a4b7d2e903` sobre `e29ba200b4ed`, con índice `(device_id, problem_type, status)` para la búsqueda que corre en cada punto rechazado.
- S4 — `persist_ingest_alert` busca o crea la alerta abierta de `(device_id, problem_type)`, agrega la ocurrencia y actualiza `latest_occurrence_at`. La organización se copia de `devices.organization_id`.
- S5 — Recurrencia: si no hay alerta abierta pero sí una cerrada del mismo par, la nueva se enlaza a la más reciente por `previous_alert_id`.
- S6 — `GET /alerts`: alertas abiertas con dispositivo, problema, organización, cantidad de ocurrencias y última ocurrencia. Scoped por organización; `platform_admin` ve todas.
- S7 — `POST /alerts/{id}/close`: cierra (`status=closed`, `closed_at=now`). Exige `org_admin`, responde `404` sobre una alerta ajena y `400` si ya estaba cerrada.

## Tasks

- T1 — S1, S2, S3: modelos + migración — inline.
- T2 — S4, S5: `persist_ingest_alert` y los dos call-sites de la ingesta — inline.
- T3 — S6, S7: router `/alerts` registrado en `main.py` — inline.
- T4 — 9 tests en `tests/test_alerts.py` — inline.

## Log

- L1 — user: "que tienen esas ramas viejas?" y después "dale" al plan de borrar las obsoletas y portar alertas.
- L2 — La implementación original vive en `feat/ingest-alerts` (base `eee36a2`, 22/10), apilada sobre `feat/roles-and-admin`, con roles `admin/client` que `develop` ya no usa. No se mergeó: se portó el modelo, el servicio y los tests al modelo actual (organizaciones + `platform_admin`/`org_admin`/`member`).
- L3 — Diferencia con el original: la organización se resuelve desde `devices.organization_id` y no desde la asignación abierta. Con la asignación, una alerta de `no_assignment` quedaba con `organization_id NULL` y no aparecía en `GET /alerts`, que es justo el caso más frecuente.
- L4 — Verificado: migración aplicada contra Postgres, 9 tests nuevos, `GET /alerts` scoped y `member` solo lectura.
- L5 — Riesgo: 1 (cambia datos persistidos: dos tablas nuevas y `persist_ingest_alert` deja de ser un no-op). Sin migración de datos existentes.
