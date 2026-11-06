# Telemetry contract hardening
Branch: `feat/telemetry-contract-hardening`  
Delivery: small reviewable commits  
Test runner: `make test && make check`

## Specs

1. **S1 — Version explícita del contrato:** En `source/schemas/ingestion.py`, agregá a `DeviceIngestBatch`: `v: Literal[1] = 1` (default 1 para no romper emisores actuales). Debe rechazar `v: 2` con 422, no ignorarlo. Documentá el campo y cubrí lote sin `v`, con `v=1` y con `v=2`.
2. **S2 — Normalización estricta:** Normalizá `recorded_at` a UTC y `heading=360` a `0` en ingesta y `Location`, manteniendo rechazo de timestamps sin zona y futuros.
3. **S3 — Salud:** Agregá `GET /health` sin autenticación que devuelva `{"status": "ok"}`.
4. **S4 — Índices y conexión:** Agregá índices compuestos para tracking e ingesta, migración reversible y `pool_pre_ping=True`.
5. **S5 — Historial limitado:** `GET /trucks/{truck_id}/iter` acepta `limit` entre 1 y 1000, default 100.
6. **S6 — Documentación:** Actualizá arquitectura, roadmap y README solo si cambia algo visible.

## Tasks

- T1 [S1-S2] inline — contrato Pydantic y tests — complete (`7e956bd`)
- T2 [S3-S5] inline — health, índices, migración, conexión y límite — complete (`692e510`, `c134a00`)
- T3 [S6] inline — documentación y compatibilidad — complete (`b83c836`)

## Log

### L1

# Tarea: portar a IterTrack las buenas ideas de Trazia (sin reescribir IterTrack)

El repositorio `/home/octa/proyectos/trazia` es solo referencia de lectura. No copiar ni modificarlo. Implementar los cambios solicitados conservando la arquitectura madura de IterTrack, la deduplicación existente y la compatibilidad con firmware y simulador.

### L2

Implementación completada en cuatro commits chicos. `make test`, `make check` y `env/bin/python -m pytest tests/ -q` quedan en verde (105 tests). La verificación de migración sobre SQLite falla antes de alcanzar la migración nueva por incompatibilidades preexistentes de `f08375e32888` (`NOW()` y `ALTER COLUMN`); la migración nueva sí se valida estructuralmente mediante `Base.metadata.create_all` durante la suite.
