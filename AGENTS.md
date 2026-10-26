# AGENTS.md - Guía e Instrucciones para Agentes de Inteligencia Artificial

Este documento define el contexto, las reglas arquitectónicas, los estándares de código y las restricciones de seguridad que **todo agente de IA** (Antigravity, Claude Code, Cursor, Copilot, etc.) debe seguir estrictamente al interactuar con el repositorio **IterTrack**.

---

## 1. Visión General del Proyecto

* **Nombre:** IterTrack
* **Propósito:** Plataforma de rastreo y telemetría satelital GPS para camiones y flotas en tiempo real.
* **Componentes Principales:**
  1. **Backend:** API REST construida con **FastAPI** (`source/`).
  2. **Persistencia:** Base de datos relacional **PostgreSQL** administrada mediante **SQLAlchemy 2.0** y **Alembic** (`source/models/`, `alembic/`).
  3. **Autenticación:** Sistema **OAuth2 + JWT** con hashing bcrypt (`source/services/auth.py`, `source/models/user.py`, `source/schemas/auth.py`). Dependencias: `python-jose[cryptography]`, `passlib[bcrypt]`.
  4. **Visualización / Frontend:** SPA en **React 19 + TypeScript + Vite** (`frontend/`), compilada a `frontend/dist` y servida por FastAPI. Mapa en tiempo real con **Leaflet + MapLibre** (OpenFreeMap), marcador cenital del camión (WebP recortado, importado como asset), rotación según rumbo y tamaño escalado con el zoom. El recorrido del camión seleccionado se dibuja en rojo (`#d64545`) **solo cuando se pide desde la sección Rutas** (botón "Ver recorrido" → `verRecorrido` del contexto del dashboard); por defecto el mapa muestra únicamente la ruta por hacer. Se traza sólo el **último tramo continuo** (`splitPath` corta donde la velocidad implícita supera 200 km/h), con un círculo en el punto de partida y reinicio al cerrar la vuelta (`keepCurrentLap`: al volver a pasar a menos de 60 m del inicio del trazo, después de al menos 1 km, se descarta lo anterior). Sobre ese mismo mapa se dibuja el viaje abierto del camión seleccionado: las paradas como pines **negros** numerados (las entregadas sólo bajan de opacidad) y la ruta por calles hasta la próxima parada en azul, con `ROUTE_WEIGHT` 6 px —la recta punteada de respaldo, cuando no hay proveedor, va 4 px—. La parada a la que va el camión lleva la clase `target` y un halo animado (`@keyframes stop-halo`) que se anula con `prefers-reduced-motion`. En móvil, elegir un camión encuadra el camión junto con las paradas de su viaje (`fitSelection` de `MapView`), no sólo el camión. Al cargar, el mapa se encuadra sobre la flota una sola vez. Rutas `/`, `/register`, `/map`, `/fleet` y `/viajes`.
  5. **Simulador:** Script Python con **un circuito urbano real por camión** por Córdoba Capital (`scripts/simulate_trucks.py`, `scripts/cordoba_route.json`, `cordoba_route_norte.json`, `cordoba_route_sur.json`). `ROUTE_FILES` asigna circuito por índice de camión; si hay más camiones que circuitos, los que comparten ruta se reparten la vuelta en fases. Los trazados se piden a OSRM (OpenStreetMap) con `scripts/generate_demo_routes.py`, una herramienta de mantenimiento que no corre en el arranque. Aprovisiona un dispositivo simulado por camión y emite **solo** por `POST /devices/ingest`, el mismo camino que un ESP32; no hay camino con credenciales humanas. Saltea los camiones ocupados por un dispositivo que no creó (`SIMULATED_DEVICE_PREFIX`), de modo que el hardware real siempre gana; `--force` revoca al ocupante y obliga a re-aprovisionar ese equipo. Cada corrida arranca con el recorrido vacío: el simulador borra el historial de sus propios camiones (`DELETE /trucks/{id}/iter`) antes del primer punto, y `--keep-history` lo conserva. Antes de cada tramo pide `GET /trips/{id}/route` y **conduce esa misma geometría**, así el trayecto real coincide con el que dibuja el mapa y pasa por las paradas en orden; si no hay viaje abierto, no hay proveedor de ruteo o la API falla, recorre su circuito fijo como respaldo. Los camiones con hardware real se saltean antes de ese paso, así que su historial nunca se toca.
  6. **Hardware Embebido:** Firmware C++ para microcontroladores **ESP32** con **PlatformIO** (ubicado en la rama `origin/IterTrack-Hardware`).

---

## 2. Entorno de Ejecución y Dependencias

* **Ruta del Entorno Virtual:** `/home/octa/IterTrack/env`
* **Binarios que DEBES usar para ejecutar comandos:**
  * Python: `env/bin/python`
  * Uvicorn: `env/bin/uvicorn`
  * Alembic: `env/bin/alembic`
  * Pip: `env/bin/pip`
* **Regla:** Nunca asumas que las dependencias están en el Python global del sistema. Ejecuta siempre a través de `env/bin/...` o activando el entorno (`source env/bin/activate`).
* **Actualización de dependencias:** Si agregas una biblioteca, agrégala tanto al código como a `requirements.txt`.

---

## 3. Ramas y Flujo de Trabajo Git

* `main`: Rama de producción / código estable.
* `develop`: Rama activa de desarrollo e integración (backend HTTP, base de datos, esquemas y frontend).
* `IterTrack-Hardware`: Rama dedicada exclusivamente al firmware ESP32 y código PlatformIO (`Iter-Hard/`).

### Mensajes de commit

* **Siempre en español.** El prefijo conventional (`feat`, `fix`, `docs`, `refactor`, `chore`, `test`) queda en inglés porque lo consume el tooling; la descripción va en español neutro y en modo imperativo: `fix(simulador): renovar el JWT de admin antes de recuperar un dispositivo`.
* Sin atribución de IA y sin `Co-Authored-By`.
* Un commit por unidad de trabajo revisable: el código con sus tests y su documentación juntos.

---

## 4. Estándares de Arquitectura y Separación de Capas

El backend en `source/` sigue una separación estricta de responsabilidades:

1. **Modelos ORM (`source/models/`):**
   * Usan la sintaxis moderna de **SQLAlchemy 2.0** (`Mapped[T] = mapped_column(...)`).
   * Todos los modelos deben heredar de `Base` (`source.database.database`).
   * No mezclar lógica de serialización HTTP dentro de los modelos ORM.

2. **Esquemas de Validación (`source/schemas/`):**
   * Definidos con **Pydantic v2** (`BaseModel`).
   * Utilizados para validación de entrada en requests y formateo de respuestas JSON.
   * Deben incluir validación estricta (ej. límites geográficos para latitud/longitud con `Field(..., ge=..., le=...)`).

3. **Capa de Base de Datos (`source/database/`):**
   * `config.py`: Manejo centralizado de variables de entorno mediante `pydantic_settings.BaseSettings`.
   * `database.py`: Definición de `engine`, `SessionLocal`, `Base` y la función generadora `get_db()`.
   * Inyección de dependencia obligatoria en endpoints: `db: Session = Depends(get_db)`.

4. **Controladores / Servicios (`source/services/`):**
   * Agrupados en `APIRouter` con prefijos y etiquetas claras (`tags=["trucks"]`, `tags=["auth"]`).
   * Los endpoints deben responder con los códigos de estado HTTP semánticos correspondientes (`200`, `201`, `400`, `401`, `404`, etc.) usando `raise HTTPException(...)` en lugar de devolver diccionarios con `"error": ...` y estado `200 OK`.

5. **Autenticación (`source/services/auth.py`):**
   * Implementada con **OAuth2 Password Flow + JWT**.
   * Las utilidades (hashing bcrypt, creación/verificación de tokens, `get_current_user`) y los endpoints (`/auth/register`, `/auth/login`, `/auth/me`) conviven en el mismo archivo para mantener la simplicidad.
   * La configuración JWT se centraliza en `source/database/config.py` mediante variables de entorno: `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
   * Para proteger un endpoint de otro servicio, importar la dependencia: `from source.services.auth import get_current_user`.
   * Las contraseñas nunca se almacenan en texto plano — se hashean con bcrypt antes de persistir en la tabla `users`.
   * El `response_model=UserResponse` en endpoints garantiza que `hashed_password` nunca se expone en respuestas JSON.
   * `POST /auth/register` exige un `invitation_code` de una organización con invitación activa (no revocada ni vencida); ya **no** crea organizaciones. El campo `org_name` fue retirado de `UserCreate`.

6. **Organizaciones e invitaciones (`source/services/organizations.py`):**
   * `User.role` tiene tres valores con alcance explícito y un `CHECK CONSTRAINT` (`ck_users_role`) que rechaza cualquier otro: `platform_admin` (dueño de la plataforma), `org_admin` (administrador de una organización) y `member` (lectura). Las dependencias `require_platform_admin`, `require_org_admin` y `require_org_admin_or_platform` nombran el alcance que exige cada endpoint.
   * `POST /organizations` exige `platform_admin`. `GET /organizations` devuelve solo la propia para `org_admin`. El resto de los endpoints de organización (`GET /organizations/{id}/invitation`, `POST /organizations/{id}/invitation/rotate`, `DELETE /organizations/{id}/invitation`) exigen `org_admin` y responden `404` sobre una organización ajena para no filtrar su existencia.
   * El alta de camión para un cliente `org_admin` es `POST /trucks` (siempre en su organización). El alta en nombre de otra organización es `POST /organizations/{id}/trucks` y exige `platform_admin`; `PATCH /trucks/{id}/organization` (transferir un camión entre empresas) también es exclusivo de `platform_admin`.
   * Cada organización tiene **un único código rotable** en `organizations.invitation_code`. La vigencia se calcula con `Organization.invitation_active`: revocada (`invitation_revoked_at`) o vencida (`invitation_expires_at`) deja de servir.
   * Rotar genera un código nuevo y limpia la revocación; revocar conserva el código pero lo invalida. Los códigos sin fecha de expiración nunca vencen.

7. **Frontend React (`frontend/`):**
   * La UI es una SPA de **React 19 + TypeScript + Vite** en `frontend/`; se compila a `frontend/dist` con `npm --prefix frontend run build` (o `make frontend`).
   * `source/main.py` sirve ese build: `GET /`, `GET /register`, `GET /map` y `GET /fleet` devuelven `frontend/dist/index.html` (React Router resuelve la ruta) y `/assets/*` monta los archivos hasheados con `StaticFiles`. Si el build no existe, esos endpoints responden `503` con el comando para generarlo.
   * El único asset estático restante es `source/static/isologo.png`, servido en `/favicon.ico` con `include_in_schema=False`.
   * **Assets de imagen del frontend:** van en `frontend/src/assets/` y se importan (`import truckWebp from '../assets/truck.webp'`) para que Vite los emita con hash en `frontend/dist/assets/`. **Nunca** en `frontend/public/`: el build los deja en la raíz del sitio (`/truck.webp`), que FastAPI no sirve, y en producción el `<img>` queda roto con un `404`. El `tests/test_static_css.py` verifica que el marcador se emita bajo `assets/` y que no quede ninguna referencia a la raíz.
   * **Secciones autenticadas:** `App.tsx` monta `DashboardLayout` (sidebar + topbar + `DashboardProvider`) como layout de ruta y cada sección es un `<Outlet>` que monta su propio contenedor. El provider vive en el layout, no en la página: cambiar de sección no reinicia el polling ni pierde la selección. El mapa también vive en el layout y se oculta con `.mapbox-off` (`visibility:hidden` en escritorio, `display:none` bajo 1265 px): montarlo en la página del panel lo recreaba en cada visita, con Leaflet + MapLibre nuevos y el estilo de OpenFreeMap pedido de nuevo. Las secciones sin mapa llevan `.app-section`: gradiente de fondo propio y tarjetas más translúcidas (`--g-bg`), para que el `backdrop-filter` tenga algo que difuminar. La sección Camiones vive en `/fleet` porque `GET /trucks` ya es el endpoint JSON; `Rutas`, `Reportes` y `Ajustes` se muestran deshabilitadas (`aria-disabled`, `title="Próximamente"`) hasta que tengan página.
   * El login es client-side: `LoginPage` envía usuario/contraseña a `POST /auth/login` como `application/x-www-form-urlencoded`, guarda el `access_token` en `localStorage` (clave `itertrack_token`) y navega a `/map`.
   * El registro es client-side: `RegisterPage` pide nombre completo/usuario/email/contraseña **y el código de invitación** y los envía a `POST /auth/register` como JSON; ante un `201` hace login automático, guarda el token y navega a `/map`. Muestra el `detail` de la API como texto (nunca `innerHTML`).
   * La protección de `/map` es client-side: `DashboardProvider` valida el token contra `GET /auth/me` al montar; sin token o con `401` limpia el storage y redirige a `/`.
   * En desarrollo, Vite (`:5173`) proxya `/auth`, `/trucks`, `/devices` y `/health` a `http://localhost:8000` (ver `frontend/vite.config.ts`). En producción se sirve el build desde FastAPI.
   * `frontend/dist` está en `.gitignore`: no se commitea el build.

8. **Dispositivos GPS (`source/services/devices.py`, `source/schemas/device.py`):**
   * La autenticación del hardware es independiente del login humano: `Authorization: Bearer <token>` contra `POST /devices/ingest`. El token se muestra una sola vez y se guarda solo como hash SHA-256.
   * Administración (solo `admin`): `GET /devices`, `POST /devices` (`identifier`, `truck_id`), `POST /devices/{id}/reassign`, `POST /devices/{id}/token/rotate`, `POST /devices/{id}/revoke`.
   * Invariantes: una asignación abierta por equipo y por camión (índices parciales en `device_assignments`); rotar el token invalida el anterior al instante; revocar desactiva el equipo y cierra su asignación para liberar el camión.
   * `source/services/devices.py` expone errores de dominio (`DeviceError`, `DeviceNotFoundError`) que los endpoints traducen a `400`/`404`; `scripts/provision_device.py` los imprime como texto.
   * **Alertas de ingesta (`source/models/alert.py`, `source/services/alerts.py`):** cada punto rechazado se agrupa en la alerta abierta de `(dispositivo, tipo de problema)` y queda como `alert_occurrence` con su evidencia. Una alerta cerrada que vuelve a fallar abre una nueva enlazada por `previous_alert_id`. `GET /alerts` lista las abiertas de la organización (todas para `platform_admin`); `POST /alerts/{id}/close` exige `org_admin` y responde `404` sobre una alerta ajena. La organización se copia del dispositivo, así que una alerta de `no_assignment` también queda scoped.

9. **Arranque, demo y despliegue:**
   * `scripts/bootstrap_platform.py` crea la organización interna y la cuenta `platform_admin`. Se corre **una vez por despliegue** y converge si se repite. Sin esto, una base vacía no tiene forma de emitir una invitación.
   * `scripts/seed_demo.py` crea o resetea (`--reset`) el tenant `Demo Corp`: `org_admin`, `member`, camiones y dispositivos `SIM-<id>`. Cada camión tiene **patente propia** (`TRUCK_PLATES`, por defecto `ABC123`, `DEF456`, `XYZ789`) para poder buscarlo; la lista la comparten el seed y el simulador, y el seed renombra si cambia. También siembra tres dadores de carga, un depósito (`Depósito Centro`, Plaza San Martín) y **un viaje por camión** (`DEMO-001/002/003`) con paradas tomadas del mismo circuito del simulador y ya resueltas: sin ellos la sección Rutas queda vacía y sin forma de crear el primero desde la UI. Las paradas de cada viaje salen del tercio del circuito que le toca a ese camión (los camiones comparten ruta con fases distintas), así que el mapa muestra destinos propios al seleccionar cada uno. El último viaje se siembra `done` para que quede un camión disponible y el formulario tenga a quién asignarle un viaje nuevo. El seed reescribe las paradas si cambiaron. `--renew` (cron cada 15 min en la demo) reinicia el mismo viaje de cada camión que terminó, sin crear filas: el progreso automático los cierra en ~11 minutos y clonar dejaría cientos de viajes por día. Nunca toca otras organizaciones ni la cuenta de plataforma, y falla si un camión o dispositivo ya pertenece a otra organización.
   * `Dockerfile` multi-stage: Node compila `frontend/dist`, Python corre la app. El entrypoint (`scripts/docker_entrypoint.sh`) migra, bootstrapea y siembra según `RUN_MIGRATIONS`, `BOOTSTRAP_PLATFORM` y `SEED_DEMO_ON_BOOT`, y después ejecuta el comando recibido.
   * `docker-compose.yml`: `caddy` (TLS), `web` (migra), `worker` (simulador, `RUN_MIGRATIONS=false`) y `postgres` (volumen nombrado, **sin puertos publicados**). La imagen se publica en GHCR desde `.github/workflows/publish-image.yml`.
   * El runbook operativo está en `docs/DEPLOYMENT.md`.

10. **Destinos y viajes tercerizados (`source/services/destinations.py`, `source/models/destination.py`):**
   * `chargers` es el dador de carga (la empresa que terceriza el envío). Es una dimensión de la organización, **no** un inquilino: no tiene login ni invitaciones.
   * `trips` une dador, fecha, camión y chofer. **El chofer va en el viaje, no en el camión**: en tercerización el mismo camión rota de chofer por envío.
   * `external_ref` es idempotente por organización: un envío reenviado dos veces responde `409` en lugar de duplicarse.
   * **La coordenada es la fuente de verdad; la dirección es texto para mostrar.** Se resuelve una sola vez al importar y se guarda en `address_cache` por dirección normalizada (sin acentos, minúsculas). Reimportar la misma dirección no consulta al proveedor.
   * Lo que el geocoder no encuentra queda `needs_review=true` en `GET /destinations/pending`. No se inventa un centroide: un pin equivocado manda al chofer al lugar incorrecto.
   * El pin manual (`PATCH /trips/{id}/stops/{stop_id}`) resuelve el destino y **escribe la caché** con `resolved_by_user_id`.
   * El proveedor vive detrás de la interfaz `Geocoder` (`source/services/geocoding.py`), inyectada con `Depends(get_geocoder)`. `GEOCODER_PROVIDER` acepta `none` (default, no llama a nadie) y `nominatim`. Los tests siempre la sobrescriben y nunca salen a la red.
   * `trips.departure_at` es `datetime` con zona (no una fecha): "salir a las 07:30" no entra en un `date` y sin zona la salida se corre tres horas.
   * `depots` guarda nombre, lat/lng y `radius_m`. La **elegibilidad** de un camión no usa el radio: está disponible si está activo y no tiene viaje en `planned`/`in_progress` (`GET /trips/available-trucks`). El radio del depósito sí se usa para detectar la llegada (ver progreso automático).
   * Lecturas con `get_current_user` y scoping por organización; escrituras con `require_org_admin`. Así `member` puede ver viajes pero no crearlos, y la sección Rutas le oculta el formulario.
   * La instancia pública de Nominatim no sirve en producción: 1 request/segundo y 4 por minuto para scripts periódicos. El análisis y las alternativas están en `odd/tasks/destinations.md`.
   * **Ruta por calles (`source/services/routing.py`):** `GET /trips/{id}/route` devuelve la geometría, la distancia y la duración del tramo hasta **la próxima parada** del viaje: arranca en la última posición medida del camión (o en el depósito si no reportó) y apunta a la primera parada `pending` con coordenada, en orden de `seq`. Una parada ya alcanzada (`arrived`) no se vuelve a pedir: el camión está en su radio y lo que sigue es la siguiente. El viaje es secuencial: no se dibuja el atajo a una parada posterior ni se puede entregar una parada antes que la anterior (`trip_progress._next_pending_stop`). La respuesta incluye `stop_id` y `stop_seq` para que el mapa sepa a qué parada apunta. El proveedor vive detrás de `Router` y se inyecta con `Depends(get_router)`; `ROUTING_PROVIDER` acepta `none` (default, el mapa dibuja una recta punteada) y `osrm` (`ROUTING_URL`, instancia propia en producción: la pública es solo para la demo). Sin origen o sin paradas ubicadas responde `409`; proveedor sin configurar `503`; proveedor caído o sin ruta `502`. El mapa recibe `[lat, lng]` ya ordenados y nunca reinterpreta el formato de OSRM. La ruta se pide al cambiar la selección, cuando cambia el estado de alguna parada y cuando el camión se aleja más de 120 m de la geometría guardada; en cada latido el trazo se recorta en la posición actual del camión.
   * **Reset del viaje:** `POST /trips/{id}/reset` (solo `org_admin`) deja el viaje `planned` y todas sus paradas `pending`, sin fechas de llegada ni salida. Lo usa el simulador al arrancar, para que una corrida nueva no herede las entregas de la anterior.
   * **Progreso automático (`source/services/trip_progress.py`):** cada punto aceptado por la ingesta mueve el viaje abierto del camión, **siempre en orden**: sólo se evalúa la primera parada `pending`/`arrived` (`_next_pending_stop`), así pasar cerca de la 3 antes de llegar a la 1 no marca nada. Entrar al radio del depósito (`depots.radius_m`) lo pasa a `in_progress`; entrar a 120 m de esa parada la marca `arrived` y salir la marca `delivered`; cuando todas están `delivered` el viaje queda `done`. Una parada sin coordenada se saltea y mantiene el viaje abierto. La transacción es del llamador: el módulo no hace commit.

---

## 5. Reglas Críticas de Seguridad y Secretos

1. **Nunca exponer secretos:**
   * **JAMÁS** escribas contraseñas reales, tokens o claves de base de datos en archivos rastreados por Git (`source/`, `alembic.ini.example`, etc.).
   * `.env` y `alembic.ini` están en `.gitignore`. Verifica siempre que tus cambios no intenten forzar su inclusión en Git.
   * Si agregas una nueva variable de configuración, regístrala con valores genéricos en [`.env.example`](./.env.example) y en `source/database/config.py`.
2. **Validación de entradas:**
   * Nunca confíes en los datos recibidos de clientes o módulos GPS externos. Valida tipos, formatos, longitudes y rangos numéricos.
3. **Prevención de Inyección:**
   * Utiliza siempre el ORM de SQLAlchemy o consultas parametrizadas. Nunca concatenes strings en consultas SQL.

---

## 6. Guía para Cambios en Base de Datos (Alembic)

Cuando modifiques o crees modelos en `source/models/`:
1. Asegúrate de que el nuevo modelo esté importado en `alembic/env.py` para que `target_metadata = Base.metadata` lo detecte.
2. Genera la migración con Alembic:
   ```bash
   env/bin/alembic revision --autogenerate -m "descripcion_del_cambio"
   ```
3. Revisa el archivo generado en `alembic/versions/` para validar las instrucciones `upgrade()` y `downgrade()`.
4. Aplica la migración:
   ```bash
   env/bin/alembic upgrade head
   ```

---

## 7. Deuda Técnica Conocida y Tareas Prioritarias

Si estás realizando refactorizaciones o corrigiendo bugs en el proyecto, ten en cuenta los siguientes puntos pendientes:

* **Migración BD en `tracking.py` (Completada):**
  * Todos los endpoints de `source/services/tracking.py` (`POST /trucks`, `GET /{truck_id}/location`, `GET /{truck_id}/iter`, `GET /trucks`, `GET /trucks/ids`) consultan y persisten exclusivamente en PostgreSQL mediante la sesión inyectada `db: Session = Depends(get_db)`. La escritura de telemetría vive solo en `POST /devices/ingest`.
* **Autenticación OAuth2 + JWT (Completada):**
  * Modelo ORM `User` en `source/models/user.py` (tabla `users` creada vía migración `391c6b7b75c0`).
  * `source/schemas/auth.py` y `source/services/auth.py` implementados: registro, login (OAuth2PasswordRequestForm), `/auth/me`, hashing bcrypt y tokens JWT HS256.
  * Configuración JWT centralizada en `source/database/config.py`: `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (60).
  * `auth_router` incluido en `source/main.py`.
  * Todos los endpoints de `tracking.py` (`POST`, `PUT`, `GET` y `DELETE` bajo `/trucks`) requieren `Depends(get_current_user)` y Bearer JWT. La SPA se sirve sin autenticación HTTP; el frontend de `/map` valida el token y envía el Bearer en las llamadas a la API.
  * Cada usuario pertenece a una organización y los camiones nuevos se asignan a ella; los listados se filtran por organización y las operaciones sobre camiones existentes verifican esa pertenencia. `platform_admin` es el único rol que puede leer datos de todas las organizaciones; `org_admin` administra solo la suya y `member` solo lee. Los dispositivos también guardan `organization_id` (tomado del camión al aprovisionarlos) para poder filtrarlos sin recorrer las asignaciones.
  * `bcrypt` fijado en `4.0.1` en `requirements.txt` por incompatibilidad de passlib 1.7.4 con bcrypt 5.x.
* **Invitaciones por organización (Completada):**
  * Migración `5426d9d8a15a` agrega `organizations.invitation_expires_at` e `invitation_revoked_at`; `Organization.invitation_active` calcula la vigencia.
  * `source/services/organizations.py` expone `GET/POST /organizations`, `GET /organizations/{id}/invitation`, `POST /organizations/{id}/invitation/rotate` y `DELETE /organizations/{id}/invitation`, todos con `get_current_admin_user`.
  * `POST /auth/register` ya no crea organizaciones: exige un código activo. Un código revocado o vencido responde `400` `"Código de invitación inválido"`.
  * Tests en `tests/test_organizations.py` y `tests/test_auth.py`; el detalle de diseño está en `odd/tasks/invitation-codes.md`.
* **Ciclo de vida de dispositivos GPS (Completada):**
  * Endpoints admin en `source/services/devices.py`: `GET /devices`, `POST /devices`, `POST /devices/{id}/reassign`, `POST /devices/{id}/token/rotate` y `POST /devices/{id}/revoke`.
  * El token en claro solo se devuelve al crearlo o rotarlo; la base guarda únicamente su hash SHA-256. Rotar invalida el token anterior y revocar cierra la asignación abierta.
  * Tests en `tests/test_devices_admin.py`; el detalle de diseño está en `odd/tasks/device-lifecycle.md`.
* **Manejo de Errores Semántico (Completado):**
  * `add_truck` ahora lanza `HTTPException(status_code=400, ...)` en duplicados.
* **Validación de Coordenadas (Completada):**
  * `source/schemas/truck.py` valida `lat` entre `-90` y `90` y `long` entre `-180` y `180` con `Field(ge=..., le=...)`.
* **CI/CD con GitHub Actions (Completada):**
  * Workflow en `.github/workflows/ci.yml`. Se ejecuta en `push` y `pull_request` sobre `main` y `develop`, y también manualmente (`workflow_dispatch`).
  * Steps: creación del virtualenv `env/`, `pip install -r requirements.txt`, setup de Node 22, `make frontend`, `make check` y `make test`.
  * **Los targets del `Makefile` invocan `env/bin/python`**, por eso el workflow crea el venv antes de ejecutarlos; sin ese paso falla en el primer step.
  * No requiere servicio de PostgreSQL: `tests/conftest.py` usa SQLite en memoria con `dependency_overrides`.
  * La rama `IterTrack-Hardware` queda fuera de los triggers a propósito: no contiene tests Python.
* **Dependencias duplicadas en `requirements.txt` (Resuelto):**
  * Se eliminó `psycopg` (v3); el proyecto usa un único driver: `psycopg2-binary` (`postgresql+psycopg2://`).
* **Paquetes sin uso en `requirements.txt` (Resuelto):**
  * Eliminados `fastar`, `rignore`, `detect-installer` y `fastapi-cloud-cli` (sin referencias en `source/`, `scripts/` ni `tests/`).
* **Sentry removido (Resuelto):**
  * Se eliminó `sentry-sdk` de `requirements.txt` y del venv: estaba instalado pero nunca se integraba. Si en el futuro se necesita monitoreo, se agrega la integración completa, no solo el paquete.
* **Lint y typechecking en Python (Completado):**
  * `make check` corre `ruff` e `mypy` sobre `source`, `scripts` y `tests`; la configuración vive en `pyproject.toml` (`check_untyped_defs`, `warn_unused_ignores` y el plugin `pydantic.mypy`).
  * Ignorados a propósito: `E501` (no se reflowea código legado) y `B008` (`Depends(...)` en defaults es el idiom de FastAPI). `alembic/versions/` está excluido por ser código generado y `scripts/selfcheck.py` ignora `E402` porque inserta `ROOT` en `sys.path` antes de importar la app.
  * El frontend sí tiene typechecking y lint: `npm --prefix frontend run build` corre `tsc` y `npm --prefix frontend run lint` corre `oxlint`.
* **Cobertura de tests de autenticación (Resuelto):**
  * `tests/test_auth.py` cubre registro, login, `/auth/me` y protección de endpoints, incluidos casos de validación y credenciales no autorizadas.
* **Telemetría de velocidad y rumbo (Implementada):**
  * `Location` admite `speed` y `heading`; ambos valores se guardan en cada punto de tracking. La integración del hardware puede enviar estos campos cuando estén disponibles.
* **Registro en el navegador (Completada):**
  * `/register` sirve la SPA; `RegisterPage` hace el registro + auto-login y navega a `/map`. El flujo completo está descrito en la sección 4.6.
* **Migración a React (Completada):**
  * Se retiró la UI vanilla (`source/static/js/`, `source/static/css/` y las páginas `login.html`, `register.html`, `map.html`, `map-mobile.html`). La SPA vive en `frontend/` y FastAPI sirve `frontend/dist` (sección 4.6). El historial completo está en `odd/tasks/react-frontend-migration.md`.

---

## 8. Comandos Útiles para Agentes

* **Lint y typecheck de Python (ruff + mypy):**
  ```bash
  make check        # ruff check + mypy sobre source, scripts y tests
  ```
  Equivalente directo:
  ```bash
  env/bin/python -m ruff check source scripts tests
  env/bin/mypy source scripts tests
  ```
* **Compilar el frontend (necesario para servir `/`, `/register` y `/map`):**
  ```bash
  make frontend        # npm ci && npm run build en frontend/
  ```
  Si `frontend/dist` no existe, FastAPI responde `503` en esas rutas y los tests
  de SPA se saltean.

* **Correr exactamente lo que corre el CI (local):**
  ```bash
  make frontend && make check && make test
  ```
  Si esto pasa en local, el workflow de GitHub Actions pasa en el runner.
* **Comprobar carga de configuración:**
  ```bash
  env/bin/python -c "from source.database.config import settings; print('Config OK')"
  ```
* **Iniciar servidor de desarrollo:**
  ```bash
  env/bin/uvicorn source.main:app --reload --port 8000
  ```
* **Ver la flota moviéndose (migra, siembra demo, levanta API y simula):**
  ```bash
  make demo    # un solo comando; Ctrl+C corta la simulación
  ```
  Reutiliza la API si ya responde en `:8000` y toma `ADMIN_API_USER`/`ADMIN_API_PASSWORD` del `.env` raíz.
* **Ejecutar simulación de camiones:**
  ```bash
  make simulation                             # contra una API ya levantada
  env/bin/python scripts/simulate_trucks.py   # emite por /devices/ingest, mismo camino que un ESP32
  ```
* **Bootstrap de plataforma y demo (idempotentes):**
  ```bash
  env/bin/python -m scripts.bootstrap_platform
  env/bin/python -m scripts.seed_demo
  env/bin/python -m scripts.seed_demo --reset
  ```
  Se invocan como módulo (`-m`) porque `source` no está en `sys.path` al ejecutar el archivo suelto.
* **Levantar el stack completo (requiere Docker):**
  ```bash
  docker compose up -d
  docker compose logs -f web
  ```

---

## 9. Política de Testing (obligatoria)

* Todo endpoint nuevo o modificado debe incluir tests en `tests/` (pytest).
* Los tests usan SQLite en memoria con `dependency_overrides` de `get_db` y `get_current_user` (ver `tests/conftest.py`).
* Correr antes de terminar cualquier tarea: `make test` y `make check`.
* Cambios en `frontend/`: correr `npm --prefix frontend run lint` y `npm --prefix frontend run build` (typecheck + build).
* Los tests que verifican el servido de la SPA y las regresiones de CSS necesitan `frontend/dist` (generado con `make frontend`) y se saltean si no existe.
* Se agradece cubrir: caso feliz + validación inválida (422) + duplicados/no encontrado (400/404).

## 10. Checklist para Endpoints Nuevos

1. Validación con Pydantic en `source/schemas/` (rangos con `Field(ge=..., le=...)`).
2. `db: Session = Depends(get_db)` en la firma.
3. Endpoints de escritura protegidos con `Depends(get_current_user)`.
4. `HTTPException` con códigos semánticos (400/401/404/422).
5. Tag del router correcto.
6. Test asociado en `tests/`.

## 11. Roadmap del Producto

Ver [ROADMAP.md](./ROADMAP.md) para la visión completa: dashboard web de flota, estadísticas logísticas y alertas de seguridad (desvíos, caída de combustible, geocercas). Todo desarrollo nuevo debe alinearse con esa hoja de ruta.
