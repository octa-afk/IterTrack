# ROADMAP — IterTrack

## Visión de producto

IterTrack es una plataforma de rastreo y telemetría satelital GPS para camiones y flotas en tiempo real. El objetivo final es entregar al cliente una **web de seguimiento de flota** con estadísticas logísticas y alertas de seguridad (anti-robo: desvíos de ruta, caída de combustible, etc.).

## Fases

### Fase 1 — Tracking (actual) ✅
- API REST con FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic.
- Registro de camiones, actualización y consulta de ubicación, historial.
- Mapa en vivo (`/map`) con Leaflet + OpenStreetMap.
- Simulador de ruta urbana (`scripts/simulate_trucks.py`).

### Fase 2 — Identidad y acceso
- Auth OAuth2 + JWT (en progreso/completado).
- Roles por cliente (dueño de flota, operador, solo lectura).
- Cada camión pertenece a un cliente/organización (multitenancy).

### Fase 3 — Dashboard web
- Frontend web para seguir la flota en tiempo real.
- **A definir stack**: extender el HTML estático actual, SPA (React/Vue) consumiendo la API, o SSR con FastAPI + Jinja2.
- Fichas por camión: ubicación, estado, historial de viajes.

### Fase 4 — Estadísticas logísticas
- Km recorridos por período, consumo estimado, tiempos de viaje, paradas.
- Comparativas entre camiones / conductores / períodos.
- Exportación de reportes.

### Fase 5 — Alertas de seguridad
Motor de alertas con reglas configurables por cliente:
- **Desvío de ruta**: vehículo fuera de corredor planificado (distancia > umbral).
- **Caída de combustible**: descenso anómalo del nivel reportado por el hardware.
- **Salida/entrada de geocerca**.
- **Parada prolongada** en zona no autorizada.
- **Exceso de velocidad** (requiere campo `speed` en Location).
- Notificaciones: email / webhook / push (a definir).

## Definiciones a validar con el cliente
- Qué cuenta exactamente como "desvío" (km fuera de ruta, tiempo, destino).
- Umbral de "nafta baja / caída" (nivel absoluto vs. caída brusca).
- Frecuencia de reporte esperada de los dispositivos GPS.
- Roles y permisos necesarios.

## Principios
- Todo dato de ubicación es **sensible**: proteger con auth, no exponer endpoints públicos de escritura.
- Las alertas deben ser explicables (por qué disparó, qué dato lo provocó).
