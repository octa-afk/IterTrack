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

### L5 — Revisión nativa de la rama (2026-10-23)

`review assess` sobre `877cac7..HEAD` con escalada del ítem 2 (seguridad): tier `high`, `review_due: true`. Consentimiento del usuario: **revisar este cambio**. Lentes: `risk`, `readability`, `reliability`.

El refutador confirmó un hallazgo **CRITICAL** y abrió una corrección acotada (42 líneas): al transferir un camión entre organizaciones, `Device.organization_id` no se resincronizaba, así que el tenant anterior conservaba el dispositivo y podía rotarlo o revocarlo, mientras el nuevo no podía verlo ni aprovisionar un reemplazo. Corregido en `0a41eb1` y cubierto por `test_truck_transfer_moves_assigned_device_to_the_new_organization`.

El validador dirigido aprobó; autoridad quemada con `review.acknowledge-approved`. Suite: 168 tests.

Follow-ups informativos (no bloquean, trabajo posterior):
- **Bootstrap de `platform_admin`** — tras la migración no existe ninguno, así que `POST /organizations` y el alta cross-org quedan inalcanzables hasta crear la primera cuenta por SQL. Es exactamente el bloque 2: confirma su prioridad.
- El pass-through de `platform_admin` en `_ensure_device_scope`/`_ensure_truck_scope` es inalcanzable porque `reassign`/`rotate`/`revoke` exigen `org_admin`. Es intencional según la matriz, pero conviene borrar la rama muerta o documentar por qué está.
- La política "ocultar como 404" está expresada en tres helpers con mecanismos distintos (`HTTPException` en organizaciones, `DeviceNotFoundError` en dispositivos, inline en `create_device`).
- El enum de roles aparece en cuatro copias (modelo, `CHECK`, y dos `UPDATE` de la migración) y `ROLE_VALUES` no lo consume nadie.
- `org_router` (alta de camiones) vive en `tracking.py` pero monta bajo el prefijo `/organizations`, que ya administra `organizations.py`.
- El `downgrade` mapea `platform_admin` a `cliente` (pérdida inevitable: el rol viejo no tiene inverso). Documentado acá.

Ya corregido tras la revisión: las dos aserciones de test debilitadas (detalle exacto del rol y `404` exacto en reassign cross-org) y tres tests nuevos que fijan el `organization_id` al aprovisionar y el rechazo de aprovisionar sobre un camión ajeno.

### L6 — Bloque 2: bootstrap y seed separados (2026-10-23)

Decisión del usuario: "el demo es para el cliente y el deploy para mi". Dos scripts con ciclos de vida distintos:

- `scripts/bootstrap_platform.py` → organización interna `IterTrack` + `platform_admin`, **una vez por despliegue**. Converge si se repite (no duplica, promueve el rol si el usuario existía). La invitación de la organización interna queda revocada a propósito: nadie se registra en la plataforma.
- `scripts/seed_demo.py` → tenant `Demo Corp` con `org_admin`, `member`, camiones y dispositivos asignados. `--reset` lo rebarré sin tocar otras organizaciones ni la cuenta de plataforma.

Las credenciales salen del entorno (`.env.example` documenta el contrato); ninguna va hardcodeada. Se invocan como módulo (`python -m scripts.…`) porque `source` no está en `sys.path` al ejecutar el archivo suelto. Targets nuevos: `make bootstrap`, `make seed-demo`, `make reset-demo`.

Los camiones del seed usan la convención de `build_truck_configs` (`ABC123-01`…, ids desde 1), que es exactamente lo que espera el simulador con sus defaults — así el seed y la simulación no se desincronizan.

Hallazgo durante los tests: con ids fijos, el seed **adoptaba** un camión de otra organización que tuviera el mismo id. Ahora falla con `SeedError` en vez de robar datos ajenos; hay un test que lo fija.

Evidencia: 10 tests en `tests/test_platform_setup_scripts.py`; suite completa **178 passed**; `make check` limpio (40 archivos). Verificación contra la Postgres local: bootstrap creado y repetido sin duplicar; seed creado y luego `--reset`, con `Demo Fleet` (org 2) y sus 3 camiones intactos después del reset.

### L7 — Bloque 3: modo dispositivo del simulador (2026-10-23)

Motivo: el usuario aclaró que el simulador es la flota de desarrollo (no solo la demo) y que convive con ESP32 reales. El modo anterior escribía por `PUT /trucks/{id}/location`, que **no** pasa por el pipeline del hardware: sin token de dispositivo, sin resolución de asignación, sin dedupe por `batch_id`+`sequence`, sin puntos rechazados ni alertas, sin auditoría en `ingested_points`.

Diseño: el loop de ruta recibe un *sender* (`enviar(lat, lon, velocidad, rumbo, medido_en) -> bool`) y deja de conocer el transporte.

- `--mode user` (default, sin cambios de comportamiento): sender = `actualizar_ubicacion` con renovación de token.
- `--mode device`: `preparar_dispositivo()` + `constructor_de_sender(token)`; emite por `POST /devices/ingest` con `batch_id` UUID y `sequence` incremental.

Coexistencia: un camión tiene una sola asignación abierta (`uq_device_assignments_open_truck`). El simulador reconoce sus dispositivos por `SIMULATED_DEVICE_PREFIX` + id de camión (`SIM-001`) y **saltea** cualquier camión ocupado por otro dispositivo, así el ESP32 real siempre gana. `--force` revoca al ocupante, con advertencia explícita de que hay que volver a aprovisionar ese equipo.

Se unificó la convención de nombres: el seed ahora nombra los dispositivos `SIM-<truck_id:03d>` (antes `DEMO-DEVICE-<índice>`), que es exactamente lo que calcula el simulador. Sin eso, el modo dispositivo habría considerado los dispositivos del seed como hardware ajeno y habría salteado toda la demo.

Evidencia: 9 tests en `tests/test_simulate_device_mode.py`; suite completa **187 passed**; `make check` limpio (41 archivos). Prueba end-to-end contra la API local en el puerto 8010: 58 puntos en `ingested_points`, 0 rechazados, `tracking_points` actualizados con velocidad y rumbo; y con un prefijo distinto el simulador salteó el camión ocupado y abortó sin tocar nada.

### L8 — Bloque 4: Dockerfile y entrypoint (2026-10-23)

Antes de escribirlo se resolvieron dos bloqueantes reales:

1. `alembic.ini` está en `.gitignore`, así que el contenedor no podía migrar. El Dockerfile copia `alembic.ini.example`; `alembic/env.py` sobrescribe `sqlalchemy.url` con `settings.database_url`, así que el placeholder nunca se usa y no hay riesgo de filtrar credenciales.
2. No existía `.dockerignore`: el contexto se llevaba `env/` (235 MB) y `frontend/node_modules` (155 MB), y era la vía para que un `.env` entrara en la imagen. Ahora el contexto son 22 MB.

Diseño:
- Stage `frontend` (node:22-alpine): `npm ci` + `npm run build`. Se copian primero los manifiestos para cachear dependencias.
- Stage `runtime` (python:3.12-slim): instala `requirements.txt`, copia `source/`, `scripts/`, `alembic/`, `alembic.ini.example → alembic.ini` y el `dist` del stage anterior. Usuario no root (`appuser`, uid 1001), `HEALTHCHECK` contra `/health` usando `urllib` (sin instalar curl).
- `scripts/docker_entrypoint.sh`: `alembic upgrade head` si `RUN_MIGRATIONS=true` (default), bootstrap si `BOOTSTRAP_PLATFORM=true`, seed sin reset si `SEED_DEMO_ON_BOOT=true`, y después `exec "$@"`. Sin comando, arranca uvicorn en `${PORT:-8000}`.

El worker de la demo usa la misma imagen con comando propio y `RUN_MIGRATIONS=false`, para que dos procesos no compitan por la migración:

    python -m scripts.simulate_trucks --mode device --count 3 --id 1 --interval 2

Verificado:
- Build del frontend (`npm --prefix frontend run build`) correcto.
- `scripts/docker_entrypoint.sh` ejecutado localmente con el venv en el PATH: migra, converge el bootstrap, siembra de forma idempotente y ejecuta el comando recibido.
- Ensayo de despliegue completo en una base **vacía** y temporal (`itertrack_rehearsal`, creada y eliminada): `alembic upgrade head` → bootstrap (dos veces) → seed → `seed --reset` → app levantada en el puerto 8011 → `/health` OK → login de `demo-admin` y de `owner` → el `org_admin` ve 1 organización, 3 dispositivos y 3 camiones, y recibe `403` al intentar crear una organización → el `platform_admin` ve `Demo Corp` e `IterTrack`. 8/8 verificaciones.

Límite honesto: **Docker no está instalado en esta máquina**, así que la imagen no fue construida ni ejecutada. Lo verificado es la secuencia de arranque y el entrypoint, no `docker build`.

### L9 — Bloque 5: compose, TLS y publicación de la imagen (2026-10-23)

Host elegido: **Azure for Students** (VM B1s, 750 h/mes gratis 12 meses, sin tarjeta) con Docker Compose. Se descartó AWS: su free tier 2026 da hasta USD 200 pero **la cuenta se cierra sola a los 6 meses**. Se eligió VM + Docker sobre un PaaS para no quedar atado: la imagen se publica en **GHCR**, no en Azure Container Registry, y el dominio queda fuera de Azure.

`docker-compose.yml` con cuatro servicios:

- `postgres` — volumen nombrado `pgdata`, **sin puertos publicados** (solo red interna). Acceso desde una laptop únicamente por túnel SSH.
- `web` — la imagen, `RUN_MIGRATIONS=true`, bootstrap y seed de demo activados. Es el único que migra.
- `worker` — misma imagen, `command` propio con `--mode device`, `RUN_MIGRATIONS=false` para no competir con la migración del web, `API_URL=http://web:8000/trucks` por red interna.
- `caddy` — 80/443, TLS automático, volúmenes `caddy_data` y `caddy_config`.

`Caddyfile` usa `{$DOMAIN}`: con un dominio real obtiene el certificado solo; con `localhost` cae a CA interna.

`.github/workflows/publish-image.yml` publica en `ghcr.io/<owner>/itertrack` con `GITHUB_TOKEN` y `packages: write`. La VM solo hace `pull`, así el build (que necesita RAM) no ocurre en la B1s de 1 GB.

`scripts/simulate_trucks.py` ahora devuelve `False` y `main()` sale con código 1 cuando no puede autenticarse, para que el orquestador vea un fallo en lugar de un éxito. Hay un test que lo fija.

`deploy/.env.example` documenta todas las variables de la VM, separando las credenciales públicas de la demo de las privadas de plataforma.

Verificado: YAML parseado y estructura afirmada (4 servicios, Postgres sin `ports`, worker en modo device y sin migrar, volúmenes correctos, workflow con `packages: write`); suite completa **187 passed** y `make check` limpio. **No verificado**: `docker compose config` e `docker build`, porque Docker no está instalado.

### L10 — Sincronización de documentación (2026-10-23)

La documentación había quedado desactualizada y en dos puntos **afirmaba lo contrario de lo que hace el código**:

- README decía que `POST /auth/register` aceptaba `org_name` para crear una organización. Eso se retiró hace varios commits.
- README y ROADMAP decían que "los permisos por rol siguen pendientes". Se implementaron en el bloque 1.

Cambios:

- **`README.md`**: roles y alcance explícitos (tabla de tres roles y las cuatro reglas que el backend hace cumplir), sección de modos del simulador, paso 7 de instalación (bootstrap + seed, con la explicación del círculo vicioso de la primera cuenta), tabla de API ampliada con organizaciones y ciclo de vida de dispositivos, sección **Demo Pública** con las credenciales que sí son públicas, sección **Despliegue**, y `SECRET_KEY` mínima de 32 caracteres en seguridad.
- **`docs/DEPLOYMENT.md`** (nuevo): runbook completo —qué se despliega, por qué Azure y por qué no AWS, reglas de portabilidad, prerrequisitos, primer despliegue, checklist de verificación, operación (logs, reset, backup, túnel SSH, update), rollback, mudanza a otro host, costos y vencimiento, y qué variables son públicas y cuáles no.
- **`docs/ARCHITECTURE.md`**: sección 4 suma el alcance explícito del rol; sección 5 reescrita con `Device.organization_id`, la regla del `404` y la resincronización de dispositivos al transferir un camión.
- **`AGENTS.md`**: nuevo punto 4.9 (arranque, demo y despliegue) y comandos de bootstrap, seed y Docker en la sección 8.
- **`ROADMAP.md`**: Fase 2 marcada como implementada en permisos por rol; Fase 6 nueva con la demo pública y lo que le falta.









### L11 — Auditoría y reescritura de historia antes de publicar (2026-10-23)

Antes de abrir el repositorio se auditó **todo el historial**, no el árbol actual: lo que se borró en un commit sigue siendo público en un repo publicado. Un script recorrió los 1.504 blobs de texto alcanzables desde las 12 refs, buscando claves privadas, tokens (GitHub, AWS, Slack, OpenAI), URLs con credenciales, JWTs, SAS de Azure, `secret_key`, passwords asignadas, emails y rutas absolutas.

**Resultado: ningún secreto real.** Todos los hallazgos fueron placeholders (`postgres://usuario:tu_password@host`, `postgres:password@host/railway`), código (`password: string`, `password = os.getenv(...)`), fixtures de test (`password="insecure"`) o rutas `/home/octa/` que coinciden con el handle público. Confirmado además: ningún `.env` real fue commiteado nunca; `.gitignore` cubre `.env`, `.env.*` y `alembic.ini`; sin volcados ni binarios; el firmware ESP32 no tiene WiFi hardcodeado; la captura `mapa-en-vivo.png` del historial (mapa de Córdoba, sin navegador ni datos) se inspeccionó a ojo.

**Lo único que sí quedaba expuesto:** el email institucional en el campo author de 185 de 188 commits.

Decisión: **reescribir la historia** para reemplazarlo por el noreply de GitHub. Procedimiento:

1. `git bundle create` de respaldo con las 8 ramas (`/tmp/opencode/pre-rewrite.bundle`, 2,1 MB).
2. Clon espejo de `origin` y `git filter-repo --email-callback` mapeando `octavio.lautaro.torres@mi.unc.edu.ar` → `208891597+octa-afk@users.noreply.github.com`.
3. Verificación: **los árboles de las 8 ramas son idénticos** (mismo `^{tree}` antes y después) y los 188 commits se conservan. El contenido no cambió, solo los SHA.
4. `git push --mirror` y resincronización de las ramas locales.
5. `git config user.email` del repo apuntado al noreply; sin eso, el siguiente commit reintroducía la fuga.

Costo aceptado: todos los SHA cambian y el clon de otra máquina queda incompatible (hay que re-clonar o `reset --hard origin/<rama>`). El email ya no aparece en ningún commit, autor, committer ni mensaje.

Pendiente de decidir: 2 commits conservan el **nombre real** `Octavio Lautaro Torres` (el resto son `octa-afk`). El email ya no está, así que no compromete nada; cambiarlo exige otra reescritura.

### L12 — VM creada y stack preparado (2026-10-23)

**Diagnóstico de una hora que valía la pena documentar.** `B1s` aparecía como `NotAvailableForSubscription` en todas las regiones. La primera hipótesis (proveedores de recursos sin registrar) era cierta pero no era la causa: `Microsoft.Compute`, `Microsoft.Network` y `Microsoft.Storage` estaban `NotRegistered` y se registraron, y la cuota quedó en 0/6 vCPU, pero los SKUs seguían bloqueados.

La causa real apareció al leer el cuerpo de la respuesta que la CLI de Azure se comía con un `RuntimeError: The content for this response was already consumed`: **`RequestDisallowedByAzure`**, por la política `sys.regionrestriction` (*Allowed resource deployment regions*), que limita la suscripción a cinco regiones: `chilecentral`, `southafricanorth`, `newzealandnorth`, `canadacentral`, `northcentralus`.

Con eso, `Standard_B2ats_v2` (2 vCPU / 1 GB / x64) sí aparece disponible en `chilecentral`, y también entra en las 750 h gratuitas. Es mejor latencia que Brazil South para Córdoba.

Estado:

| Ítem | Valor |
|---|---|
| Resource group | `itertrack-rg` en `chilecentral` |
| VM | `itertrack-vm`, `Standard_B2ats_v2`, Ubuntu 24.04, disco 30 GB |
| IP pública | `57.156.58.24` (static, Standard SKU) |
| Dominio provisional | `57-156-58-24.sslip.io` (resuelve desde la VM; el resolver local no lo resuelve) |
| Acceso | SSH con `~/.ssh/itertrack_vm`, sin password; puertos 80/443 abiertos |
| En la VM | Docker 29.1.3, Compose 2.40.3, 1 GB de swap, 25 GB libres |
| Archivos | `docker-compose.yml`, `Caddyfile`, `.env` (600) en `~/itertrack` |

`docker compose config --quiet` **valida** por primera vez los artefactos Docker: 4 servicios, 3 volúmenes, imagen `:develop` interpolada desde el `.env`. Antes de esto no había Docker en la máquina local y la validación era solo de YAML.

Bloqueante: `docker manifest inspect ghcr.io/octa-afk/itertrack:develop` responde `unauthorized`, que no distingue entre paquete privado y tag inexistente. Falta que el paquete sea público o un PAT con `read:packages`, y confirmar que el run del workflow terminó en verde.

### L13 — Demo en vivo y hallazgos del primer despliegue (2026-10-23)

**https://57-156-58-24.sslip.io** — certificado de Let's Encrypt válido hasta 2027-01-21, `/health` en 200, SPA servida, login de `demo-admin` en 200.

Verificado en producción: 10 migraciones aplicadas, bootstrap de plataforma (`IterTrack` + `owner`), seed de `Demo Corp` con 3 camiones y dispositivos `SIM-001..003`, posiciones moviéndose (`-31.410801,-64.192630` → `-31.411408,-64.190641` en 6 s), y aislamiento correcto: `demo-admin` recibe `403 "Se requiere rol de administrador de plataforma"` al intentar crear una organización. `docker compose config --quiet` valida los cuatro servicios.

**Hallazgo 1 — el reset congela el mapa (bug).** `seed_demo --reset` borra y recrea los dispositivos, lo que invalida sus tokens. El simulador en modo dispositivo no reintenta: `enviar_coordenada` (modo usuario) sí maneja el 401 con `on_unauthorized`, pero `enviar_ingesta` no. Resultado: el worker entra en un bucle de `401 Invalid device credentials` y la flota se detiene hasta reiniciarlo. `docker compose restart worker` lo recupera (18 puntos en 10 s). **El cron diario de reset congelaría la demo todos los días si no se corrige.**

**Hallazgo 2 — `sslip.io` no resuelve en todas las redes.** El router de la red local devuelve `NXDOMAIN` para `57-156-58-24.sslip.io`, mientras `1.1.1.1` y el resolver de la VM lo resuelven. Para un portfolio es un riesgo real: una red corporativa o educativa con DNS filtrado vería la demo caída. Refuerza la necesidad del dominio propio (el `.me` del Student Pack).

**Hallazgo 3 — velocidades irreales.** La ruta tiene 425 puntos, 13,03 km, con espaciado irregular (media 30,7 m, máximo 162,8 m). A un punto cada 2 s, el tramo máximo implica 293 km/h, y 93 de los 424 tramos superan los 90 km/h. Se ve en el panel, que dibuja una línea de límite de 90 km/h.

**Hallazgo 4 — invitación de demo activa.** `Demo Corp` tiene un `invitation_code` activo y sin expiración, impreso en el log del seed. Cualquiera puede crear un usuario en el tenant de demo. `_reset_tenant` borra camiones, dispositivos y puntos, pero **no usuarios**, así que las cuentas creadas se acumulan entre resets.

### L14 — El reset ya no congela la flota, y el cron quedó instalado (2026-10-23)

Corregido el hallazgo 1 de L13. Primero el test (4 casos en RED), después el arreglo:

- `enviar_ingesta` acepta `on_unauthorized` y reintenta el punto **una sola vez** con el token que devuelve el callback, igual que el camino de usuario.
- `constructor_de_sender` **persiste** ese token, así una recuperación cuesta una rotación y no una por punto.
- La recuperación reusa `preparar_dispositivo`, que ya sabía reaprovisionar un dispositivo faltante o rotar el existente, y respeta un camión tomado por hardware real.
- Una recuperación fallida se reintenta como mucho cada 30 s, para que un ESP32 real no haga que el simulador golpee la administración en cada punto.

El primer intento tenía un defecto propio: el cooldown se aplicaba también a las recuperaciones exitosas, así que **dos resets seguidos dejaban la flota parada hasta 30 s**. Corregido: solo un fallo arranca el cooldown.

Verificación en producción, con la imagen `d112f47`:

| Prueba | Resultado |
|---|---|
| Reset simple, sin reiniciar el worker | flota sigue |
| Dos resets seguidos | 3 dispositivos nuevos, **1 rotación cada uno**, flota sigue |
| Estado estable | 33 puntos OK / 0 FAIL en 20 s |
| Cron con entorno mínimo (`env -i`) | exit 0 y reset aplicado |

Cron instalado en el host (`crontab`, no systemd timer):

```
0 4 * * * cd /home/octa/itertrack && /usr/bin/docker compose exec -T web python -m scripts.seed_demo --reset >> /home/octa/reset.log 2>&1
```

Nota para el futuro: `crontab -` dentro de un script con `set -e` falló en silencio; `crontab archivo` sí funciona. Es el tipo de detalle que hace que un cron "esté instalado" y no corra nunca.

### L15 — Velocidad realista del simulador (2026-10-23)

Hallazgo 3 de L13, corregido. La ruta tiene 425 puntos con espaciado irregular (media 30,7 m, máximo 162,8 m); emitir un punto cada 2 s fijos implicaba hasta 293 km/h y 93 de 424 tramos superaban el límite de 90 que dibuja el panel.

`espera_y_velocidad` calcula la espera de cada tramo en proporción a su longitud para una velocidad objetivo, con `--interval` como piso para que los tramos cortos no martillen la API. La velocidad reportada es el objetivo en los tramos abiertos y menor en los densos, y **nunca lo supera**: el piso solo aplica donde la distancia no alcanza para llegar al objetivo.

| Métrica | Antes | Después |
|---|---|---|
| Velocidad máxima | 293 km/h | **55,0 km/h** |
| Velocidad media | — | 29,4 km/h |
| Tramos sobre 90 km/h | 93 de 424 | **0** |
| Vuelta completa | 14,2 min | 20,8 min |

Medido también en la demo en vivo tras desplegar: 39 muestras, máximo 55,0, media 23,6, ninguna sobre 90.

El test recorre la ruta real que se entrega y afirma el techo sobre cada tramo, así que editar las coordenadas no puede reintroducir el problema en silencio.

### L16 — Acceso de un click y cierre de la invitación (2026-10-23)

Hallazgo 4 de L13 más el hueco de acceso. La página de login no mencionaba la demo: un visitante veía "Tu usuario" y no tenía forma de entrar sin leer el README, que es exactamente lo que un reclutador no hace.

`GET /config` reporta si el despliegue es una demo. El flag vive en el **servidor** y no en el build, porque la misma imagen tiene que servir a un cliente real sin el botón:

- `DEMO_MODE` es `false` por defecto. Apagado, el endpoint devuelve `{"demo":{"enabled":false}}` y ni el usuario sale del servidor.
- Encendido, devuelve usuario y contraseña de la demo y el login muestra **Entrar a la demo**, que loguea y navega al mapa.
- Las credenciales **no están en el bundle**: verificado sobre el JS servido en producción, contiene "Entrar a la demo" y cero apariciones de `demo-admin`.

Con el botón en su lugar, la invitación de `Demo Corp` deja de tener sentido. `seed_demo` ahora la crea revocada, igual que `bootstrap_platform` hace con la organización interna. En la instancia que ya existía se revocó por API: `DELETE /organizations/3/invitation` → `invitation_active: false`, y un registro con el código viejo responde `400 "Código de invitación inválido"`.

Verificado en producción: `/config` devuelve las credenciales, la invitación quedó revocada y el registro está cerrado. 206 tests, ruff y mypy limpios.

### L17 — Login de la demo: autofill, animación y mock local (2026-10-23)

Ajustes de la pantalla de login, todos en `develop`:

- **Autofill del navegador**: Chrome/Edge pintaban los campos autocompletados con fondo amarillo/oliva, rompiendo el tema oscuro. Se sobreescribió `:-webkit-autofill` con `box-shadow` inset del color `--field` y `-webkit-text-fill-color: var(--ink)` (commit `05fe0af`).
- **Animación del botón demo**: pulso suave del borde (`border-color` entre `--line` y `--acc-d`) cada 2,2 s, sin sombras ni halos, con `prefers-reduced-motion` respetado (commit `512edbf`).
- **Un solo clic, sin prellenado**: se probó prellenar usuario/contraseña desde `/config`, pero se revirtió a pedido del usuario: los campos quedan vacíos y el botón "Entrar a la demo" hace el login directo (commit `9172741`).
- **Mock de `/config` solo para desarrollo**: Vite no proxea `/config`, así que el botón no aparecía en `localhost:5173`. Se agregó un plugin `configureServer` que responde `{demo:{enabled:true,...}}` únicamente en el dev server (commit `c3d6cdd`). No afecta el build de producción.

Hallazgo local: la base de datos de desarrollo tenía aplicada la migración `c8d9e0f1a2b3` (rama `feat/ingest-alerts`, no mergeada en `develop`), por lo que `alembic upgrade head` fallaba con "Can't locate revision". La solución es recrear la base local y volver a migrar desde `develop`.

Verificado: `make check` (ruff + mypy) y `make test` (206 tests) limpios tras los cambios de frontend.

### L18 — Cadencia del simulador: off-by-one en la espera (2026-10-24)

L15 quedó verificado contra el campo `speed` que el simulador **reporta**, no contra el desplazamiento real. Al medir los puntos guardados en la base apareció un segundo problema: la espera se calculaba con el tramo que el camión acababa de recorrer, pero se aplicaba **después** de emitir el punto, así que regía el tramo siguiente.

Efecto: cada punto viajaba con el pacing del tramo anterior. Un tramo de 100 m precedido por uno de 30 m se emitía 3,1 s después del anterior, o sea 117 km/h reales con `speed=55` reportado; el panel, que mide desplazamiento, marcaba alerta por exceso de velocidad en un camión que iba a 55.

- Arreglo: `espera_hacia_el_siguiente(ruta, indice, intervalo, objetivo)` calcula la espera del tramo `indice -> indice + 1` (el último enlaza con el primero, porque la ruta es un circuito) y es la única fuente de la espera del bucle. `espera_y_velocidad` sigue calculando la velocidad reportada del tramo recorrido.
- Tests: `test_wait_after_a_point_covers_the_segment_to_the_next_point` (agenda exacta con tramos alternados) y `test_a_simulated_lap_never_exceeds_the_target_speed` (invariante sobre la ruta real: distancia/espera ≤ 55). Antes del arreglo fallaban con 251,94 km/h; el test previo no lo detectaba porque evaluaba cada tramo aislado y nunca la secuencia.

Medición sobre la ruta completa (424 tramos) y sobre puntos reales de la base:

| Métrica | Antes | Después |
|---|---|---|
| Velocidad real máxima (ruta) | 251,9 km/h | **55,0 km/h** |
| Tramos sobre 90 km/h (umbral del panel) | 56 de 423 | **0** |
| Tramos sobre 55 km/h | 101 de 423 | **0** |
| Ejemplo real | 100,5 m en 3,1 s (117 km/h) | 100,5 m en 6,7 s (54 km/h) |

`espera_y_velocidad` calcula la velocidad con la espera efectiva, así que en los tramos cortos (piso de `--interval`) el valor reportado es menor que el objetivo, y ahora coincide con lo que el panel mide.
