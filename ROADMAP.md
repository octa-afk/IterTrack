# ROADMAP — IterTrack

## Visión de producto

IterTrack es una plataforma de rastreo y telemetría satelital GPS para camiones y flotas en tiempo real. El objetivo final es entregar al cliente una **web de seguimiento de flota** con estadísticas logísticas y alertas de seguridad (anti-robo: desvíos de ruta, caída de combustible, etc.).

## Alcance del MVP

- **Escala objetivo:** flotas de **menos de 10 camiones**.
- **Datos a registrar (por ahora):** únicamente **ubicación** (latitud/longitud), **velocidad** y **dirección** (rumbo).
- **Qué queremos probar (QI):** poder **ubicar al camión en el mapa**, con un **sistema de autenticación simple**.
- El dashboard avanzado, las estadísticas, las alertas y los permisos basados en roles quedan **fuera del MVP** y se agregarán después, de forma incremental, una vez validado este núcleo con el cliente. La membresía a organizaciones y el alcance multitenant básico de los camiones ya están implementados; esto no implica permisos por rol ni amplía el alcance del MVP.

## Fases

### Fase 1 — Tracking (actual) ✅
- API REST con FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic.
- Registro de camiones, actualización y consulta de ubicación, historial.
- Mapa en vivo (`/map`) con Leaflet + OpenStreetMap.
- Simulador de ruta urbana (`scripts/simulate_trucks.py`).

### Fase 2 — Identidad y acceso
- Auth OAuth2 + JWT — completado.
- **Login y registro en el navegador: completados** (`/` y `/register`). La membresía de usuarios y el alcance de camiones por organización están implementados; los permisos por rol siguen pendientes.
- Roles por cliente (dueño de flota, operador, solo lectura) — pendiente.
- Los camiones nuevos se asignan a la organización del usuario autenticado; los listados se filtran por organización y las operaciones sobre camiones existentes verifican esa pertenencia — implementado.

### Fase 3 — Dashboard web
- Frontend web para seguir la flota en tiempo real.
- **Stack decidido: vanilla ahora, SPA después.** Seguimos con HTML/JS estático sin build tooling: el flujo JWT queda a la vista y no agregamos herramientas sin necesidad.
- **Entradas del frontend vanilla entregadas:** `/` (login), `/register` (registro) y `/map` (guard de token).
- **Migrar a SPA (Vite + React o Vue) SOLO cuando se cumpla al menos uno de estos criterios:**
  - (a) el dashboard necesita rutas propias con varias vistas,
  - (b) el estado se comparte entre 3 o más vistas independientes, o
  - (c) el cliente valida el MVP y empiezan las estadísticas de la Fase 4.
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
- **Exceso de velocidad** (el campo `speed` ya está disponible en `Location`; quedan pendientes la regla de alerta y su umbral).
- Notificaciones: email / webhook / push (a definir).

## Definiciones a validar con el cliente
- Qué cuenta exactamente como "desvío" (km fuera de ruta, tiempo, destino).
- Umbral de "nafta baja / caída" (nivel absoluto vs. caída brusca).
- Frecuencia de reporte esperada de los dispositivos GPS.
- Roles y permisos necesarios.

## Principios
- Todo dato de ubicación es **sensible**: proteger con auth, no exponer endpoints públicos de escritura.
- Las alertas deben ser explicables (por qué disparó, qué dato lo provocó).
- **Registro de contraseñas:** mínimo 12 caracteres, al menos una letra y un número (`UserCreate`). Se valida al registrarse; el login verifica contra el hash y no rechaza claves existentes por no cumplir la política. Casos en `tests/test_auth.py`.
