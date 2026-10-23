# Demo Deployment

Objetivo: convertir IterTrack en una demo pública utilizable (postulación laboral) y reutilizable como base del producto que se va a vender.
Rama de trabajo: `develop` (sin rama feature; cambios pequeños y por unidad de trabajo).
Runner: `make test` (pytest) + `make check` (ruff + mypy).

## Specs

- **S1** — `DATABASE_URL` acepta los formatos que entregan los PaaS (`postgres://user:pass@host/db` y `postgresql://…`) y los normaliza al dialecto `postgresql+psycopg2://` que exige el proyecto. Un valor ya normalizado o un `sqlite://…` se devuelve intacto.
- **S2** — `SECRET_KEY` menor a 32 caracteres aborta el arranque con un mensaje que explica el riesgo. *(Decisión de diseño, no pedida literalmente por el usuario: una demo pública con cuentas admin y HS256 permite falsificar tokens con una clave débil. Se registra como supuesto.)*
- **S3** — `scripts/.env.example` documenta `API_URL` y `AUTH_URL`. Los valores definidos en `scripts/.env` se aplican a `BASE_URL`/`AUTH_URL`, sin pisar variables ya presentes en el entorno del proceso.
- **S4** — La simulación sobrevive al vencimiento del token: ante un `401` en `PUT /trucks/{id}/location` renueva el token y reintenta **una** vez. Si el reintento también falla, reporta `False` como hoy.
- **S5** — El refresco de token se comparte entre los hilos de simulación: un solo re-login actualiza el header que ven todos los camiones.
- **S6** — `User.role` acepta únicamente `platform_admin`, `org_admin` o `member`, con `CHECK CONSTRAINT` en la base. La migración renombra `admin`→`org_admin` y `cliente`→`member`.
- **S7** — Un `org_admin` solo ve y administra su propia organización. Operar sobre otra responde `404`, no `403`, para no revelar que existe.
- **S8** — Un `platform_admin` lista todas las organizaciones y todos los dispositivos, y es el único que puede crear organizaciones.
- **S9** — El alta de camión en nombre de un cliente usa `POST /organizations/{organization_id}/trucks`, exclusivo de `platform_admin`; una organización inexistente responde `404`. `POST /trucks` sigue creando en la organización del `org_admin`.
- **S10** — Un `org_admin` no puede rotar ni revocar invitaciones ajenas, ni reasignar, rotar o revocar dispositivos ajenos.
- **S11** — Transferir un camión entre organizaciones (`PATCH /trucks/{id}/organization`) es exclusivo de `platform_admin`; un `org_admin` recibe `403`.
- **S12** — `Device.organization_id` se completa desde el camión al aprovisionar el equipo, y la migración lo rellena desde la asignación abierta o la más reciente.


## Tasks

| ID | Specs | Ruta | Estado | Evidencia |
| --- | --- | --- | --- | --- |
| T1 | S1, S2 | inline | hecho | `source/database/config.py`; `tests/test_config.py` 6/6 |
| T2 | S3 | inline | hecho | `scripts/.env.example`; verificación manual en copia temporal |
| T3 | S4, S5 | inline | hecho | `scripts/simulate_trucks.py`; 4 tests nuevos en `tests/test_simulate_trucks.py` |
| T4 | S1-S5 | inline | hecho | `make check` limpio; 149 tests pasan |
| T5 | — | inline | hecho | `SECRET_KEY` local rotado a 64 caracteres |
| T6 | S6, S12 | inline | hecho | migración `b7c1d2e3f4a5`, round-trip verificado |
| T7 | S7, S8, S10 | inline | hecho | `source/services/organizations.py`, `source/services/devices.py` |
| T8 | S9, S11 | inline | hecho | `POST /organizations/{id}/trucks`, `PATCH /trucks/{id}/organization` |
| T9 | S6-S12 | inline | hecho | `tests/test_tenant_isolation.py` 15/15; suite 165/165 |



## Log

### L1 — Pedido original (verbatim)

> ahora una de mis prioridades está siendo tener una demo utilizable y con la que pueda exponer mi codigo para poder demostrar las habilidades tecnica y postularme a un trabajo. quizas seria recomendable exponer este git como quizas es recomendable hacer otro repo. que opinas?

> no busco algo en parituclar, simplemente tener un producto que eventualmente se va a vender pero que ahora me sirve para aplicar a trabnajos de desarollo, sean cuales sean. entonces, quiero que vayamos pensando en como crear una demo

> si estoy dispuesto pero antes de dockerizar, quiero que prepares xcorrectamente las variables de entorno y las simulaciones

### L2 — Hallazgos de exploración (2026-10-23)

- No existe bootstrap de primer admin: `POST /organizations` y `GET /organizations/{id}/invitation` exigen `get_current_admin_user` (`source/services/organizations.py:54,76`) y `POST /auth/register` exige invitación (`source/services/auth.py:78-89`). Una base vacía es inaccesible. Pendiente para la etapa de deploy.
- El simulador autentica una sola vez (`scripts/simulate_trucks.py:322`); con `ACCESS_TOKEN_EXPIRE_MINUTES=60` la telemetría muere a la hora y el mapa se congela. Origen de S4/S5.
- `BASE_URL`/`AUTH_URL` se leen en import (`:14-15`) antes de que `_cargar_env_local()` corra dentro de `_login()` (`:96`), así que `API_URL`/`AUTH_URL` en `scripts/.env` se ignoran. Origen de S3.
- No hay artifacts de despliegue ni Dockerfile.
- `.env` local: `SECRET_KEY` de 22 caracteres; `DATABASE_URL` ya en `postgresql+psycopg2`.

### L3 — Implementado (2026-10-23)

T1: `Settings` normaliza `postgres://` y `postgresql://` al dialecto `postgresql+psycopg2://` y rechaza `SECRET_KEY` menor a 32 caracteres con un mensaje que nombra el riesgo (HS256 falsificable).

T2: `scripts/.env.example` documenta `API_URL` y `AUTH_URL` con el ejemplo de una demo pública. Se explicita que el entorno del proceso tiene prioridad sobre el archivo.

T3: `cargar_env_local()` corre al importar el módulo, antes de leer `BASE_URL`/`AUTH_URL`. `actualizar_ubicacion()` acepta `on_unauthorized` y reintenta una sola vez tras un 401. `simular_ruta()` refresca el dict de headers compartido en el lugar, y `ejecutar_simulaciones()` serializa el re-login con un `Lock`.

Evidencia:
- RED observado: `ImportError: cannot import name 'cargar_env_local'` y 4 fallos en `tests/test_config.py`.
- GREEN: `make check` limpio (ruff + mypy, 36 archivos) y `149 passed`.
- Manual S3: copia temporal de `scripts/` con `.env` propio → `BASE_URL` y `AUTH_URL` toman el archivo; con `API_URL` en el entorno, gana el entorno.
- Manual S2: `SECRET_KEY=corta` → `ValidationError: SECRET_KEY must be at least 32 characters`.
- `.env` local rotado a una clave de 64 caracteres (los tokens emitidos antes dejan de valer; basta volver a loguearse).

Pendiente para las próximas etapas: bootstrap del primer admin (ver L2), `Dockerfile` multi-stage, seed de demo, credenciales demo visibles en el login, reset periódico, README en inglés con GIF y URL pública.

### L4 — Bloque 1: roles y aislamiento (2026-10-23)

Decisión del usuario: ambos roles con nombres distintos (`platform_admin` / `org_admin` / `member`), un solo campo con tres valores explícitos, alta de camión cross-org por **endpoint dedicado**, y el `platform_admin` puede monitorear todas las flotas. La demo nunca expone `platform_admin`.

Implementado:
- `User.role` con `CHECK CONSTRAINT`; migración `b7c1d2e3f4a5` renombra `admin`→`org_admin` y `cliente`→`member`.
- `Device.organization_id` (nullable para filas previas), poblado desde el camión al aprovisionar.
- Dependencias `require_org_admin`, `require_platform_admin`, `require_org_admin_or_platform`.
- Organizaciones y dispositivos filtrados por organización; acceso ajeno responde `404`.
- `POST /organizations/{id}/trucks` para alta cross-org (`platform_admin`).
- `PATCH /trucks/{id}/organization` pasa a `platform_admin`: transferir un activo entre empresas no es decisión del cliente.
- `AGENTS.md` actualizado para que un agente no vuelva a leer "admin" como alcance global.

Evidencia: RED 11 fallos en `tests/test_tenant_isolation.py`; GREEN 15/15 y suite completa **165 passed**; `make check` limpio (ruff + mypy, 37 archivos). Migración aplicada a la DB local y round-trip `downgrade`/`upgrade` verificado (roles vuelven a `admin`/`cliente` y regresan a `org_admin`/`member`, la columna se agrega y se quita).

Riesgo declarado: ítem 1 (migración sobre datos existentes), ítem 2 (permisos y autorización) e ítem 3 (contrato de API: endpoint nuevo y cambio de alcance en dos rutas existentes).


