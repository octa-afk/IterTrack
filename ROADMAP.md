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
- **Login y registro en el navegador: completados** (`/` y `/register`). La membresía de usuarios, el alcance por organización y los permisos por rol están implementados.
- **Validación de contraseña en el registro:** mínimo 12 caracteres, al menos una letra y un número (`UserCreate`). Esta política se valida al registrar; el login autentica contra el hash existente y no rechaza cuentas por no cumplirla. Casos cubiertos en `tests/test_auth.py`.
- **Permisos por rol (completado):** `platform_admin`, `org_admin` y `member` con `CHECK CONSTRAINT` en la base y dependencias explícitas por endpoint. El `org_admin` administra solo su organización y un recurso ajeno responde `404`; el `platform_admin` es el único que lee todas las flotas y crea organizaciones. El alta de camión cross-org usa `POST /organizations/{id}/trucks`.
- Los camiones nuevos se asignan a la organización del usuario autenticado; los listados se filtran por organización y las operaciones sobre camiones existentes verifican esa pertenencia — implementado.

### Decisiones confirmadas — administración de vehículos
- La empresa instala el hardware GPS y es responsable de registrar y retirar los vehículos; el cliente no crea ni elimina vehículos.
- Cada integrante autorizado de la empresa tendrá su propia cuenta con permisos de administrador. No se usará una cuenta compartida, para conservar la trazabilidad de quién realizó cada cambio.
- Cada unidad GPS tendrá una credencial propia, separada de las cuentas humanas. Los equipos se instalan por largo tiempo, pero pueden reutilizarse en otro camión; el mecanismo de autenticación (token por equipo contra `POST /devices/ingest`) y la reasignación (`POST /devices/{id}/reassign`) están implementados.
- Un vehículo se conserva en el sistema y cambia entre activo e inactivo; desactivarlo no elimina su historial de tracking.
- Los usuarios del cliente se darán de alta mediante un código de invitación; no crearán organizaciones ni vehículos por cuenta propia.
- Un vehículo dado de baja queda inactivo y deja de transmitir. El backend debe rechazar nuevas ubicaciones para hacer cumplir ese estado, conservando los datos históricos.
- Estas decisiones definen el objetivo futuro y están implementadas en su mayoría: el modelo `Truck` tiene estado `active` y `POST /devices/ingest` rechaza los reportes de un camión inactivo. El alta, la activación y la reasignación de organización existen; la última es exclusiva de `platform_admin` porque transferir un activo entre empresas no es decisión del cliente.
- **Invitaciones (implementado):** las organizaciones se crean únicamente con `POST /organizations` (admin) y cada una tiene un único código rotable en `organizations.invitation_code`. `GET /organizations` lista organizaciones; `GET /organizations/{id}/invitation` inspecciona el código; `POST /organizations/{id}/invitation/rotate` genera uno nuevo; `DELETE /organizations/{id}/invitation` lo revoca. `POST /auth/register` exige un código activo: uno revocado o vencido responde `400` `"Código de invitación inválido"`. Los códigos existentes sin fecha de expiración siguen vigentes.

### Próximo frente backend — ciclo de vida y acceso
- Agregar estado activo/inactivo al vehículo y operaciones administrativas para alta, asignación a una organización y cambio de estado.
- Limitar el alta y la desactivación a cuentas individuales de administrador de la empresa; los usuarios cliente solo podrán consultar.
- Registrar usuarios cliente mediante invitaciones emitidas para su organización.
- Mantener el historial al desactivar un vehículo y rechazar nuevos reportes GPS para ese vehículo.
- **Autenticación GPS (completada):** credencial individual por equipo, independiente del login humano. Token aleatorio mostrado una sola vez y guardado solo como hash SHA-256; asignación a camiones en `device_assignments` con historial; una asignación abierta por equipo y por camión. El ciclo de vida completo ya está expuesto a administradores: `POST /devices` (alta + asignación), `GET /devices`, `POST /devices/{id}/reassign` (cierra y abre asignación), `POST /devices/{id}/token/rotate` y `POST /devices/{id}/revoke`. La ingesta por lotes sigue en `POST /devices/ingest`. `scripts/provision_device.py` continúa funcionando para uso local.
- **Tiempo de medición:** cada punto guarda `recorded_at` (medición) y `received_at` (recepción). El simulador envía `recorded_at`; el backend lo acepta opcional y valida zona horaria y que no esté en el futuro. Las lecturas de `/trucks/{id}/location` e `/trucks/{id}/iter` ordenan por `recorded_at`. Pendiente: que el dispositivo lo informe desde su GPS.
- **Contrato de telemetría v1:** la ingesta por dispositivos acepta `v` omitido o `v=1`, rechaza versiones desconocidas, normaliza timestamps a UTC y transforma `heading=360` a `0`. Se conserva la compatibilidad con el simulador y firmware actuales; versiones futuras requerirán una decisión explícita de compatibilidad.
- **Persistencia de telemetría:** se agregaron índices compuestos para historial e ingesta por camión/tiempo/id y `pool_pre_ping` para detectar conexiones inactivas. Trade-off: el índice ocupa espacio adicional, aceptable para priorizar las consultas de último punto e historial del MVP.
- **Salud operativa:** `GET /health` queda público y devuelve únicamente estado; no se agrega una comprobación de base de datos para evitar convertir el endpoint en una dependencia de disponibilidad de PostgreSQL.
- La ESP32 no usa el JWT de una cuenta humana. El token va sobre HTTPS con validación de certificado en el firmware.
- **Almacenamiento sin conexión (pendiente de diseño):** la ESP32 guarda lecturas cuando no hay conexión y las envía al volver. Implica identificador de secuencia por equipo, envío por lotes idempotente, atribución del camión por `recorded_at` y una política de descarte del buffer.
- Incluir migración y pruebas para permisos, aislamiento entre organizaciones, historial retenido y comportamiento de dispositivos inactivos.

### Fase 3 — Dashboard web (SPA entregada) ✅
- Frontend web para seguir la flota en tiempo real.
- **SPA React entregada:** React 19 + TypeScript + Vite (`frontend/`), compilada a `frontend/dist` y servida por FastAPI. Rutas `/` (login), `/register` (registro) y `/map` (panel con guard de token).
- **Estrategia revisada:** el plan original era vanilla primero y SPA solo al cumplirse ciertos criterios. Se cumplieron (a) rutas propias con varias vistas y (b) estado compartido entre vistas, así que la migración se ejecutó completa y la UI vanilla se retiró. Detalle en `odd/tasks/react-frontend-migration.md`.
- **Pendiente de esta fase:** completada. El listado y el detalle muestran el estado activo/inactivo del camión (`Inactivo`, punto gris y marcador atenuado) y el recorrido reciente: al seleccionar un camión se dibuja su traza sobre el mapa con km, duración y cantidad de puntos. Detalle en `odd/tasks/fase3-dashboard.md`.

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

### Fase 6 — Demo pública y despliegue ✅
- Dockerfile multi-stage (Node compila la SPA, Python corre la app) con entrypoint idempotente.
- `docker-compose` con Caddy (TLS), `web`, `worker` (flota simulada por el pipeline real de dispositivos) y Postgres en volumen nombrado.
- Imagen publicada en GHCR; despliegue en una VM de Azure for Students.
- Simulador con dos modos: usuario y dispositivo. En modo dispositivo saltea los camiones ocupados por hardware real.
- Botón de acceso demo en el login, reset automático cada 24 h (cron en el host) y dominio definitivo (`itertrack-demo.duckdns.org` con TLS de Caddy): completados.
- Runbook: `docs/DEPLOYMENT.md`.

## Definiciones a validar con el cliente
- Qué cuenta exactamente como "desvío" (km fuera de ruta, tiempo, destino).
- Umbral de "nafta baja / caída" (nivel absoluto vs. caída brusca).
- Frecuencia de reporte esperada de los dispositivos GPS.
- Cómo emitir, aprovisionar, revocar y rotar la credencial individual de cada GPS, y registrar sus reasignaciones entre camiones.
- Si las invitaciones necesitan múltiples códigos simultáneos por organización o auditoría por código; hoy hay un único código rotable por organización.

## Principios
- Todo dato de ubicación es **sensible**: proteger con auth, no exponer endpoints públicos de escritura.
- Las alertas deben ser explicables (por qué disparó, qué dato lo provocó).
