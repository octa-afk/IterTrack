# 🚚 IterTrack - GPS Tracking System

Sistema integral de rastreo y telemetría satelital GPS para flotas de camiones en tiempo real. Cuenta con un backend desarrollado en **FastAPI**, persistencia relacional en **PostgreSQL** mediante **SQLAlchemy 2.0** y **Alembic**, simulación de trayectorias y soporte para clientes de hardware embebido (**ESP32 / PlatformIO**).

[![CI](https://github.com/octa-afk/IterTrack/actions/workflows/ci.yml/badge.svg)](https://github.com/octa-afk/IterTrack/actions/workflows/ci.yml)

---

## 📑 Tabla de Contenidos

1. [Características](#-características)
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)
3. [Estructura del Proyecto](#-estructura-del-proyecto)
4. [Tecnologías Utilizadas](#-tecnologías-utilizadas)
5. [Requisitos Previos](#-requisitos-previos)
6. [Instalación y Configuración](#-instalación-y-configuración)
7. [Ejecución](#-ejecución)
8. [Simulación de Telemetría](#-simulación-de-telemetría)
9. [Módulo de Hardware (ESP32)](#-módulo-de-hardware-esp32)
10. [Referencia de la API](#-referencia-de-la-api)
11. [Demo Pública](#-demo-pública)
12. [Despliegue](#️-despliegue)
13. [Seguridad y Buenas Prácticas](#-seguridad-y-buenas-prácticas)
14. [Instrucciones para Agentes de IA](#-instrucciones-para-agentes-de-ia)
15. [Licencia](#-licencia)

---

## 🚀 Características

* **Registro y gestión de camiones:** Identificación única por ID y patente vehicular única.
* **Telemetría GPS en tiempo real:** Recepción continua de coordenadas, velocidad, rumbo y timestamp.
* **Panel en vivo (SPA React):** Aplicación **React 19 + TypeScript + Vite** servida por FastAPI en `/map`, con mapa **Leaflet + MapLibre** sobre OpenStreetMap, marcador cenital del camión que rota según el rumbo, se escala con el zoom y sigue automáticamente al vehículo seleccionado.
* **Navegación por secciones:** sidebar con `Panel` (mapa en vivo) y `Camiones` (tabla de flota con filtros, orden y detalle). `Rutas`, `Reportes` y `Ajustes` están visibles como próximas, sin páginas de relleno.
* **Historial de recorrido:** Almacenamiento y consulta de los últimos puntos geográficos transitados.
* **Autenticación OAuth2 + JWT:** Registro y login resueltos en el navegador (`/` y `/register`); todos los endpoints de camiones, tanto de lectura como de escritura, requieren token Bearer. Contraseñas hasheadas con bcrypt y tokens firmados con HS256.
* **Roles con alcance explícito y aislamiento por organización:** `platform_admin`, `org_admin` y `member`, reforzados por un `CHECK CONSTRAINT` en la base. Ningún listado cruza el límite de una organización y operar sobre un recurso ajeno responde `404` para no revelar que existe.
* **Persistencia Robusta:** Modelos relacionales con SQLAlchemy 2.0 y control de versiones de esquema con Alembic sobre PostgreSQL.
* **Simulador integrado con ruta realista:** Script Python con un circuito cerrado de 13 km por Córdoba Capital (425 puntos). Emite como dispositivo (`POST /devices/ingest`), el mismo camino que un ESP32; la telemetría no se escribe con cuentas humanas.
* **Ciclo de vida de dispositivos GPS:** Alta, reasignación, rotación de token y revocación. Cada equipo tiene su propia credencial (hash SHA-256, mostrada una sola vez) y una sola asignación abierta por camión.
* **Documentación interactiva automática:** Swagger UI y ReDoc nativos de FastAPI.
* **Compatibilidad IoT:** Integración diseñada para dispositivos ESP32 sobre PlatformIO.

---

## 🏗 Arquitectura del Sistema

```mermaid
flowchart TD
    subgraph Emisores["Emisores de Coordenadas"]
        HW["Dispositivo ESP32 (Iter-Hard)"]
        SIM["Simulador Python (simulate_trucks.py)"]
    end

    subgraph Backend["FastAPI Backend (source)"]
        API["FastAPI App (main.py)"]
        Router["Tracking Router (services/tracking.py)"]
        Auth["Auth Router (services/auth.py)"]
        Schemas["Pydantic Schemas (schemas/)"]
        ORM["SQLAlchemy Models (models/)"]
        DBCfg["Database Config & Engine (database/)"]
    end

    subgraph Storage["Persistencia"]
        PG[("PostgreSQL")]
        AL["Alembic Migrations"]
    end

    subgraph Clientes["Visualización / Clientes"]
        MAP["Panel React + Leaflet (frontend/)"]
        DOCS["Swagger / ReDoc (/docs)"]
    end

    HW -->|HTTP POST / PUT JSON + Bearer JWT| API
    SIM -->|HTTP POST / PUT JSON + Bearer JWT| API
    API --> Router
    API --> Auth
    Auth --> Schemas
    Auth --> ORM
    Router --> Schemas
    Router --> ORM
    ORM --> DBCfg
    DBCfg --> PG
    AL -.->|Control de Esquemas| PG
    API -->|GET /map| MAP
    MAP -->|Polling GET /trucks/... + Bearer JWT| Router
    API --> DOCS
```

---

## 📂 Estructura del Proyecto

```text
IterTrack/
├── README.md                      # Documentación principal del proyecto
├── AGENTS.md                      # Reglas, arquitectura e instrucciones para agentes de IA
├── ROADMAP.md                     # Visión de producto y fases
├── Makefile                       # test, check, frontend, migrate, dev, simulation y demo
├── requirements.txt               # Dependencias Python del proyecto
├── .gitignore                     # Filtro de exclusiones para Git
├── .env.example                   # Plantilla de variables de entorno (sin credenciales reales)
├── alembic.ini.example            # Plantilla de configuración para migraciones de Alembic
├── frontend/                      # SPA React 19 + TypeScript + Vite
│   ├── src/
│   │   ├── api/                   # Clientes tipados de /auth y /trucks
│   │   ├── components/            # Mapa, lista de flota, gráficos y tarjetas
│   │   ├── lib/                   # Helpers puros (truckIcon, movement, trucks)
│   │   ├── pages/                 # LoginPage, RegisterPage, MapPage
│   │   ├── state/                 # DashboardProvider: sesión, polling y selección
│   │   ├── styles/                # base.css, auth.css, dashboard.css
│   │   └── types/                 # Tipos del contrato de la API
│   ├── vite.config.ts             # Dev server con proxy a :8000
│   └── package.json
├── scripts/
│   ├── simulate_trucks.py         # Script para simular recorrido y envío de datos GPS
│   ├── generate_demo_routes.py    # Herramienta de mantenimiento: pide los circuitos a OSRM
│   ├── cordoba_route.json         # Circuito del camión 1 (centro / Nueva Córdoba)
│   ├── cordoba_route_norte.json   # Circuito del camión 2 (Cerro de las Rosas / Argüello)
│   └── cordoba_route_sur.json     # Circuito del camión 3 (Jardín / Av. Cruz Roja)
├── tests/                         # Suite pytest (SQLite en memoria)
├── alembic/
│   ├── env.py                     # Configuración del entorno de migración de Alembic
│   ├── script.py.mako             # Template para generación de revisiones
│   └── versions/                  # Historial de migraciones de la base de datos
└── source/
    ├── main.py                    # FastAPI: routers, SPA en /, /register, /map y /fleet, y /assets
    ├── static/
    │   └── isologo.png            # Ícono del sitio (/favicon.ico)
    ├── database/
    │   ├── config.py              # Carga de variables de entorno (DB, JWT)
    │   └── database.py            # Motor de conexión, SessionLocal y Base declarativa
    ├── models/
    │   ├── __init__.py
    │   ├── device.py              # Dispositivos GPS y asignaciones a camiones
    │   ├── ingestion.py           # Puntos ingeridos y rechazados
    │   ├── organization.py        # Organizaciones (multitenancy)
    │   ├── truck.py               # Modelos ORM: Truck y TrackingPoint
    │   └── user.py                # Modelo ORM: User
    ├── schemas/
    │   ├── __init__.py
    │   ├── auth.py                # UserCreate, UserResponse, Token
    │   ├── ingestion.py           # DeviceIngestBatch / DeviceIngestPoint (contrato v1)
    │   └── truck.py               # Truck, Location, TrackingPoint
    └── services/
        ├── auth.py                # Utilidades JWT + endpoints (/auth)
        ├── devices.py             # Ingesta por lotes con token de dispositivo (/devices)
        └── tracking.py            # Endpoints de la API (/trucks)
```

> **Nota:** El código fuente del hardware embebido se gestiona en la rama `origin/IterTrack-Hardware` dentro del directorio `Iter-Hard/`.

---

## 🛠 Tecnologías Utilizadas

* **Lenguaje:** Python 3.12+ (compatible con Python 3.14).
* **Framework Web:** [FastAPI](https://fastapi.tiangolo.com/).
* **Servidor ASGI:** [Uvicorn](https://www.uvicorn.org/).
* **Base de Datos:** [PostgreSQL](https://www.postgresql.org/).
* **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/).
* **Migraciones:** [Alembic](https://alembic.sqlalchemy.org/).
* **Validación de Datos:** [Pydantic v2](https://docs.pydantic.dev/) & [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
* **Frontend:** [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/) + [Vite](https://vite.dev/).
* **Mapa:** [Leaflet 1.9](https://leafletjs.com/) + [MapLibre GL](https://maplibre.org/) con mosaicos de OpenFreeMap.
* **Testing:** [pytest](https://docs.pytest.org/) con la base de datos de prueba anulada a SQLite en memoria.
* **Lint:** [ruff](https://docs.astral.sh/ruff/) en Python y [oxlint](https://oxc.rs/docs/guide/usage/linter) en el frontend.
* **Typecheck:** [mypy](https://mypy-lang.org/) con el plugin de pydantic en Python, y `tsc` en el frontend.
* **Cliente HTTP de pruebas:** [Requests](https://requests.readthedocs.io/).
* **Autenticación:** [python-jose](https://python-jose.readthedocs.io/) (JWT), [passlib](https://passlib.readthedocs.io/) + bcrypt.
* **Hardware:** [PlatformIO](https://platformio.org/) / C++ / ESP32 (Arduino framework).

---

## 📋 Requisitos Previos

1. **Python 3.12 o superior** instalado en el sistema.
2. **Servidor PostgreSQL** en ejecución local o remoto con una base de datos creada (ej. `itertrack`).
3. **Node.js 22 o superior** (solo para compilar el frontend con Vite).
4. **Git** instalado.

---

## ⚙️ Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone git@github.com:octa-afk/IterTrack.git
cd IterTrack
```

### 2. Crear y Activar el Entorno Virtual

```bash
python3 -m venv env
source env/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Copia el archivo de ejemplo y edita las credenciales según tu entorno local:

```bash
cp .env.example .env
```

Edita el archivo `.env`:

```env
DATABASE_URL=postgresql+psycopg2://usuario:tu_password@localhost:5432/itertrack
SECRET_KEY=una_clave_secreta_aleatoria_y_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

> **Importante:** Genera una `SECRET_KEY` aleatoria segura (ej. `python -c "import secrets; print(secrets.token_urlsafe(32))"`) y no la compartas ni la subas a Git.

### 5. Configurar Alembic y Aplicar Migraciones

Genera tu archivo `alembic.ini` a partir de la plantilla:

```bash
cp alembic.ini.example alembic.ini
```

Aplica las migraciones para crear las tablas en PostgreSQL:

```bash
alembic upgrade head
```

### 6. Compilar el Frontend

FastAPI sirve el build de React desde `frontend/dist`. Sin ese build, `/`, `/register`, `/map` y `/fleet` responden `503`.

```bash
make frontend   # npm ci && npm run build en frontend/
```

`frontend/dist` está en `.gitignore`: no se commitea, así que cada clon nuevo necesita este paso una vez.

### 7. Crear el primer administrador y la demo

Una base recién migrada no tiene usuarios, y el registro exige un código de invitación que solo puede emitir un administrador. Ese círculo se rompe con `bootstrap_platform`, que crea la organización interna y la cuenta dueña de la plataforma:

```bash
env/bin/python -m scripts.bootstrap_platform
env/bin/python -m scripts.seed_demo        # opcional: tenant de demo
```

Ambos leen credenciales del entorno (ver `.env.example`) y son idempotentes: correrlos de nuevo no duplica nada. Targets equivalentes: `make bootstrap`, `make seed-demo`, `make reset-demo`.

---

## ▶️ Ejecución

Inicia el servidor con Uvicorn:

```bash
uvicorn source.main:app --reload --port 8000
```

El servidor quedará disponible en `http://127.0.0.1:8000` y sirve tanto la API como la SPA. Necesita `frontend/dist` compilado (paso 6); si falta, las rutas de la SPA responden `503`.

### 📖 Documentación Interactiva

Una vez iniciado el servidor, puedes interactuar directamente con los endpoints y el mapa desde el navegador:

* **Login:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (acceso al mapa; el enlace "Registrate" lleva a `/register`)
* **Panel en Vivo:** [http://127.0.0.1:8000/map](http://127.0.0.1:8000/map) (la SPA valida la sesión y consulta la API con Bearer JWT)
* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### 🧑‍💻 Desarrollo del Frontend

Para trabajar en la UI con recarga en caliente, levanta la API en `:8000` y el dev server de Vite en paralelo:

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

Vite proxya `/auth`, `/trucks`, `/devices` y `/health` a `http://localhost:8000` (ver `frontend/vite.config.ts`), así que el navegador no necesita configuración extra.

### 🧪 Pruebas

```bash
make frontend && make check && make test   # build + ruff/mypy + pytest
npm --prefix frontend run lint             # oxlint
npm --prefix frontend run build            # typecheck (tsc) + build
```

`make check` corre `ruff` e `mypy` sobre `source`, `scripts` y `tests`; su configuración vive en `pyproject.toml`. Los tests de pytest usan SQLite en memoria y no requieren PostgreSQL. Los tests que verifican el servido de la SPA y las regresiones de CSS se saltean si `frontend/dist` no existe.

---

## 🛰 Simulación de Telemetría

El repositorio incluye un simulador para verificar la recepción y visualización continua de telemetría en tiempo real. Emite **solo** por `POST /devices/ingest` con el token de un dispositivo aprovisionado, el mismo camino que un ESP32: no existe forma de inyectar ubicaciones con una cuenta humana.

### Camino corto: un solo comando

```bash
make demo
```

Migra la base, bootstrapea la plataforma, siembra el tenant demo (incluye dadores de carga, el `Depósito Centro` y un viaje por camión), levanta la API en `:8000` si no está respondiendo y arranca el simulador con la flota completa. Abrí `http://localhost:8000/map` y los camiones se mueven por Córdoba; `Ctrl+C` corta la simulación (y la API, si la levantó ese mismo target). Las credenciales salen del `.env` raíz (`ADMIN_API_USER` / `ADMIN_API_PASSWORD`); si ya tenés un `uvicorn` corriendo, lo reutiliza en vez de pelear por el puerto.

Para ajustar la flota sin tocar el archivo:

```bash
make demo SIMULATION_COUNT=5 SIMULATION_INTERVAL=1
```

### Camino manual

Antes de ejecutarlo, inicia el backend como administrador de la organización, que es quien registra camiones y aprovisiona el dispositivo simulado.

```bash
# El simulador lee ADMIN_API_USER y ADMIN_API_PASSWORD desde scripts/.env.
```
# Copiá la plantilla y completá con una cuenta administradora local:
cp scripts/.env.example scripts/.env

# También podés pasarlas por entorno, con prioridad sobre el archivo:
export ADMIN_API_USER=admin
export ADMIN_API_PASSWORD=tu_clave_local

# Ejecución estándar (2 segundos por ping):
python scripts/simulate_trucks.py

# Simulación a mayor velocidad (ej. 1 segundo entre pings):
python scripts/simulate_trucks.py -i 1.0

# Asignar ID o patente personalizada:
python scripts/simulate_trucks.py --id 1 --plate "ABC123" -i 1.5
```

Si `ADMIN_API_USER` o `ADMIN_API_PASSWORD` no están definidas ni en el entorno ni en `.env`, el simulador aborta con un mensaje explícito y sale con código 1, para que un orquestador lo vea como un fallo.

### Cómo emite

El simulador aprovisiona un dispositivo por camión (`SIM-<id>`) y emite por `POST /devices/ingest`, el mismo pipeline que el hardware. **Saltea** los camiones ocupados por un dispositivo que no creó, de modo que un ESP32 real siempre gana; `--force` revoca al ocupante y obliga a re-aprovisionar ese equipo.

```bash
make simulation                      # solo el simulador, contra una API ya levantada
make simulation SIMULATION_COUNT=1   # un camión, para probar el marcador
```

`make simulation` carga el `.env` raíz, así que toma `ADMIN_API_USER` y `ADMIN_API_PASSWORD` de ahí sin exports manuales.

### Características de la simulación:
1. **Rutas Urbanas Reales:** Cada camión recorre su propio circuito cerrado por Córdoba Capital: centro / Nueva Córdoba ([`cordoba_route.json`](./scripts/cordoba_route.json), 14 km), Cerro de las Rosas / Argüello ([`cordoba_route_norte.json`](./scripts/cordoba_route_norte.json), 18 km) y Jardín / Av. Cruz Roja ([`cordoba_route_sur.json`](./scripts/cordoba_route_sur.json), 14 km). Los tres están georreferenciados punto por punto y se generan con [`scripts/generate_demo_routes.py`](./scripts/generate_demo_routes.py) usando OSRM; los datos derivan de OpenStreetMap (ODbL).
2. **Telemetría Completa:** Muestra en tiempo real el rumbo en grados (°), punto cardinal (N, SE, etc.), velocidad calculada en km/h y estado HTTP (`200 OK`).
3. **Bucle Continuo:** Al completar su circuito, cada camión reinicia la vuelta siguiente sin interrupciones.

---

## 🚚 Destinos y viajes tercerizados

Cuando la flota terceriza camiones, los destinos no los define el operador: los
manda un **dador de carga** (por ejemplo, una empresa de colchones) y el operador
nos los reenvía. El modelo separa tres cosas que antes estaban mezcladas:

* `chargers` — el dador de carga. Es una dimensión de la organización, **no** un
  inquilino: no tiene login ni invitaciones.
* `trips` — el envío con su fecha, el camión asignado y el chofer. **El chofer
  vive en el viaje, no en el camión**: en tercerización el mismo camión rota de
  chofer según el envío.
* `trip_stops` — los destinos, con dirección, coordenada, procedencia y si
  necesitan revisión.

La sección **Rutas** (`/viajes`) lista los viajes y, para `org_admin`, ofrece el
formulario de alta: dador de carga, camión disponible, destino y hora de salida.
Un camión es elegible si está activo y no tiene viaje abierto; el radio del
depósito todavía no se chequea porque depende de telemetría fresca. `member` ve
la lista sin formulario.

La regla central: **la coordenada es la fuente de verdad, la dirección es texto
para mostrar**. Se resuelve una sola vez, al importar, y se guarda en
`address_cache` por dirección normalizada; la segunda importación de la misma
dirección no vuelve a consultar al proveedor. Si el proveedor no la encuentra
—"Ruta 9 km 720" no geocodifica ni con Google—, el destino queda en la cola
`GET /destinations/pending` y se resuelve con un pin manual, que a su vez
alimenta la caché.

El proveedor de geocoding está detrás de la interfaz `Geocoder` (inyectada con
`Depends`) y se elige por `GEOCODER_PROVIDER` (`none` | `nominatim`). El default
es `none`: no se llama a ningún servicio externo y todo destino queda pendiente.
La instancia pública de Nominatim no sirve en producción (1 request/segundo y 4
por minuto para scripts periódicos); el análisis completo está en
[`odd/tasks/destinations.md`](./odd/tasks/destinations.md).

---

## 🔌 Módulo de Hardware (ESP32)

El desarrollo del firmware para dispositivos en cabina de camión se encuentra en la rama dedicada `origin/IterTrack-Hardware`:

* **Directorio:** `Iter-Hard/`
* **Entorno:** PlatformIO con framework Arduino sobre placa `esp32dev`.
* **Propósito:** Lectura de módulo GPS serial (NMEA), empaquetado de payload JSON y despacho HTTP/MQTT al servidor central.

Para ver el código del módulo de hardware:

```bash
git checkout IterTrack-Hardware
```

---

## 📡 Referencia de la API

| Método | Endpoint | Descripción | Cuerpo de la Petición (Ejemplo) | Auth |
|---|---|---|---|---|
| `GET` | `/` | SPA React (`frontend/dist/index.html`) — login | — | — |
| `GET` | `/register` | SPA React — registro | — | — |
| `GET` | `/map` | SPA React — panel; valida la sesión antes de consultar la API | — | — |
| `GET` | `/fleet` | SPA React — sección Camiones (tabla de flota) | — | — |
| `GET` | `/viajes` | SPA React — sección Rutas (viajes y alta de viaje) | — | — |
| `GET` | `/chargers` | Dadores de carga de la organización | — | 🔒 Bearer |
| `POST` | `/chargers` | Crea un dador de carga | `{"name": "Colchones Sur"}` | 🔒 org_admin |
| `GET` | `/trips` | Viajes de la organización (`?charger_id=`, `?truck_id=`) | — | 🔒 Bearer |
| `POST` | `/trips` | Importa un viaje con sus destinos; geocodifica al entrar | `{"charger_id": 1, "departure_at": "2026-10-26T07:30:00-03:00", "external_ref": "ENVIO-001", "stops": [{"address": "Av. Colón 1234, Córdoba"}]}` | 🔒 org_admin |
| `GET` | `/trips/{id}` | Un viaje con sus destinos | — | 🔒 Bearer |
| `PATCH` | `/trips/{id}/stops/{stop_id}` | Pin manual: resuelve el destino y escribe la caché | `{"lat": -31.4135, "lng": -64.1811}` | 🔒 org_admin |
| `GET` | `/destinations/pending` | Cola de destinos sin coordenada (`needs_review`) | — | 🔒 Bearer |
| `GET` | `/depots` | Depósitos de la organización | — | 🔒 Bearer |
| `POST` | `/depots` | Crea un depósito | `{"name": "Depósito Centro", "lat": -31.4135, "lng": -64.1811}` | 🔒 org_admin |
| `GET` | `/trips/available-trucks` | Camiones activos sin viaje abierto | — | 🔒 Bearer |
| `GET` | `/favicon.ico` | Ícono de la pestaña del navegador (`source/static/isologo.png`) | — | — |
| `GET` | `/health` | Estado del servicio (`{"status": "ok"}`) | — | — |
| `GET` | `/assets/{archivo}` | CSS y JS hasheados del build de React | — | — |
| `POST` | `/auth/register` | Registra un usuario con un `invitation_code` activo | Ver JSON de registro abajo | — |
| `POST` | `/auth/login` | Login OAuth2 (form-data) y devuelve JWT | `username` / `password` (form) | — |
| `GET` | `/auth/me` | Datos del usuario autenticado | — | 🔒 Bearer |
| `POST` | `/trucks` | Registra un nuevo camión y su punto inicial | Ver JSON abajo | 🔒 Bearer |
| `PUT` | `/trucks/{truck_id}/location` | Agrega un punto de ubicación al historial del camión | `{"lat": -31.416, "long": -64.183, "speed": 0, "heading": 0}` | 🔒 Bearer |
| `GET` | `/trucks/{truck_id}/location` | Obtiene el punto de tracking más reciente (por `recorded_at`) | — | 🔒 Bearer |
| `GET` | `/trucks/{truck_id}/iter` | Obtiene hasta 100 puntos, del más nuevo al más antiguo (por `recorded_at`) | — | 🔒 Bearer |
| `DELETE` | `/trucks/{truck_id}/iter` | Elimina los puntos de tracking del camión, no el camión | — | 🔒 Bearer |
| `GET` | `/trucks` | Lista los camiones de la organización del usuario autenticado | — | 🔒 Bearer |
| `GET` | `/trucks/ids` | Lista IDs y patentes de los camiones de la organización del usuario autenticado | — | 🔒 Bearer |
| `POST` | `/devices/ingest` | Ingesta por lotes de telemetría, autenticada con el token del dispositivo (no JWT humano) | `{"v": 1, "batch_id": "<uuid>", "points": [{"sequence": 1, "lat": -31.416, "long": -64.183, "speed": 0, "heading": 0, "recorded_at": "2026-01-01T12:00:00Z"}]}` | 🔑 Token de dispositivo |
| `GET` | `/organizations` | Lista organizaciones: la propia para `org_admin`, todas para `platform_admin` | — | 🔒 admin |
| `POST` | `/organizations` | Crea una organización | `{"name": "Fletera Nueva"}` | 🔒 `platform_admin` |
| `GET` | `/organizations/{id}/invitation` | Consulta el código de invitación | — | 🔒 admin |
| `POST` | `/organizations/{id}/invitation/rotate` | Genera un código nuevo | `{"expires_in_days": 30}` | 🔒 `org_admin` |
| `DELETE` | `/organizations/{id}/invitation` | Revoca el código vigente | — | 🔒 `org_admin` |
| `POST` | `/organizations/{id}/trucks` | Alta de camión en nombre de otra organización | Mismo JSON que `POST /trucks` | 🔒 `platform_admin` |
| `PATCH` | `/trucks/{id}/activate` | Activa o desactiva un camión | `{"active": false}` | 🔒 `org_admin` |
| `PATCH` | `/trucks/{id}/organization` | Transfiere un camión entre organizaciones | `{"organization_id": 3}` | 🔒 `platform_admin` |
| `GET` | `/devices` | Lista dispositivos: los propios o todos según el rol | — | 🔒 admin |
| `POST` | `/devices` | Alta de dispositivo y asignación a un camión; devuelve el token una sola vez | `{"identifier": "GPS-001", "truck_id": 1}` | 🔒 admin |
| `POST` | `/devices/{id}/reassign` | Reasigna el dispositivo a otro camión | `{"truck_id": 2}` | 🔒 `org_admin` |
| `POST` | `/devices/{id}/token/rotate` | Rota el token del dispositivo | — | 🔒 `org_admin` |
| `POST` | `/devices/{id}/revoke` | Revoca el dispositivo y libera el camión | — | 🔒 `org_admin` |

### Flujo de autenticación:

**En el navegador (camino principal):** abrí `http://127.0.0.1:8000/` e iniciá sesión, o seguí el enlace "Registrate" a `/register`; el registro inicia sesión automáticamente, guarda el token en el navegador y redirige a `/map`.

**Vía API (alternativa programática):**

1. **Registro:** `POST /auth/register` con usuario, email, nombre completo, contraseña y un `invitation_code` activo (la contraseña se persiste hasheada con bcrypt).
2. **Login:** `POST /auth/login` con `username` y `password` como *form-data*; devuelve `{"access_token": "...", "token_type": "bearer"}`.
3. **Uso del token:** incluir el header `Authorization: Bearer <access_token>` en las peticiones a los endpoints protegidos (🔒). El token expira según `ACCESS_TOKEN_EXPIRE_MINUTES` (60 min por defecto).

Ejemplo de registro con un código de invitación:

```json
{
  "username": "usuario",
  "email": "usuario@example.com",
  "full_name": "Nombre Apellido",
  "password": "<password>",
  "invitation_code": "CODIGO-DE-LA-ORGANIZACION"
}
```

`POST /auth/register` ya no crea organizaciones: exige un código activo de una organización existente. Un código revocado o vencido responde `400` `"Código de invitación inválido"`.

### Roles y alcance

`User.role` tiene tres valores con alcance explícito, reforzados por un `CHECK CONSTRAINT` en la base. Un valor fuera del conjunto es rechazado por PostgreSQL, no solo por la aplicación:

| Rol | Alcance | Puede |
|---|---|---|
| `platform_admin` | Toda la plataforma | Crear organizaciones, dar de alta camiones y dispositivos en cualquier organización, leer todas las flotas |
| `org_admin` | Una sola organización | Camiones, dispositivos, usuarios e invitaciones de la suya |
| `member` | Una sola organización | Lectura: mapa e historial |

Reglas que el backend hace cumplir en todos los endpoints:

- Un listado nunca devuelve datos de otra organización.
- Operar sobre un recurso ajeno responde `404`, no `403`: no se filtra que existe.
- `POST /trucks` siempre crea en la organización del `org_admin`; el alta en nombre de otra empresa es `POST /organizations/{id}/trucks`, exclusivo de `platform_admin`.
- Transferir un camión entre organizaciones mueve también los dispositivos asignados, para que el tenant anterior no conserve un equipo que ya no le pertenece.

### Ejemplo de Payload para `POST /trucks`:

```json
{
  "truck": {
    "id": 1,
    "plate": "ABC123"
  },
  "location": {
    "lat": -31.4166867,
    "long": -64.1834193,
    "speed": 0,
    "heading": 0
  }
}
```

---

## 🎬 Demo Pública

La demo corre en un host aislado con su propia base de datos: nada de lo que haga un visitante alcanza datos de un cliente real.

**El login tiene un botón «Entrar a la demo»**: un click y estás en el mapa, sin escribir nada. Aparece solo si el servidor tiene `DEMO_MODE=true`, así que la misma imagen corre en el despliegue de un cliente con el botón ausente. Las credenciales no están en el bundle: el frontend las pide a `GET /config`, y con la demo apagada el endpoint ni siquiera devuelve el usuario.

| Cuenta | Rol | Para qué |
|---|---|---|
| `demo-admin` | `org_admin` de `Demo Corp` | Experiencia completa: camiones, dispositivos, invitaciones |
| `demo` | `member` | Solo lectura del mapa |

Las contraseñas están en [`deploy/.env.example`](./deploy/.env.example). Son públicas por diseño; la de `platform_admin` no lo es y nunca se publica.

Qué mirar: los tres camiones de `Demo Corp` se mueven sobre un circuito de 13 km en Córdoba a una velocidad objetivo de 55 km/h, con rumbo real. El `org_admin` de la demo no puede crear organizaciones (`403`) ni ver otra empresa (`404`, para no revelar que existe).

La invitación de `Demo Corp` nace revocada: la demo se entra por el botón, no por registro, y así nadie crea cuentas que sobrevivan a los resets. Los datos se rebarrer cada 24 h con `env/bin/python -m scripts.seed_demo --reset`, que nunca toca la cuenta de plataforma ni otras organizaciones.

---

## ☁️ Despliegue

La imagen se publica en **GHCR** desde GitHub Actions y corre con **Docker Compose**: Caddy para TLS, `web` con FastAPI y la SPA, `worker` con la flota simulada, y Postgres en un volumen nombrado sin puertos publicados.

```bash
docker compose up -d
```

El runbook completo —prerrequisitos, variables, verificación, operación, backup y migración a otro host— está en **[`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md)**.

Decisiones que lo mantienen portable: imagen en GHCR y no en un registry del proveedor, dominio fuera del proveedor, Postgres en Docker y cero servicios propietarios. Mudarse de host es copiar `docker-compose.yml`, `Caddyfile` y `.env`, restaurar la base y cambiar el registro `A`.

---

## 🔒 Seguridad y Buenas Prácticas

1. **Gestión de Secretos:** 
   * **Nunca** subas archivos `.env` ni `alembic.ini` con contraseñas reales a Git. Ambos están protegidos en `.gitignore`.
   * Utiliza siempre los archivos `.example` como base para nuevos despliegues.
   * `SECRET_KEY` debe tener **al menos 32 caracteres**: con HS256, una clave corta permite falsificar un token de administrador. La aplicación se niega a arrancar si no los tiene.
   * Las credenciales de la demo (`demo`, `demo-admin`) son públicas a propósito. La de `platform_admin`, `SECRET_KEY` y `POSTGRES_PASSWORD` nunca se publican.
2. **Validación de Datos:**
   * Las coordenadas GPS deben restringirse en los esquemas Pydantic (`-90 <= lat <= 90` y `-180 <= long <= 180`).
3. **Autenticación:**
   * Implementada con OAuth2 Password Flow + JWT (HS256). Todos los endpoints `/trucks` (lectura y escritura) requieren Bearer Token; la SPA se sirve públicamente, pero `/map` valida la sesión en el navegador antes de mostrar los datos. `GET /auth/me` devuelve el usuario autenticado. La ingesta de dispositivos (`/devices/ingest`) usa un token propio por equipo, separado de las cuentas humanas.
   * Las contraseñas nunca se almacenan en texto plano: se hashean con bcrypt antes de persistir en la tabla `users`.
   * `UserResponse` garantiza que `hashed_password` nunca se expone en las respuestas.
4. **Integración Continua:**
   * Cada `push` y cada pull request sobre `main` y `develop` corre automáticamente `make check` y `make test` en GitHub Actions (`.github/workflows/ci.yml`).
   * El workflow crea el virtualenv `env/` que el `Makefile` espera y compila el frontend (`make frontend`, sobre Node 22) antes de los tests, porque FastAPI sirve `frontend/dist`. No requiere PostgreSQL: los tests usan SQLite en memoria.
   * El badge de la cabecera refleja el estado del último commit.

---

## 🤖 Instrucciones para Agentes de IA

Si eres un modelo de lenguaje o agente de código asistido (como Antigravity, Claude Code, Cursor, GitHub Copilot, etc.), consulta el archivo **[`AGENTS.md`](./AGENTS.md)** en la raíz de este repositorio para conocer:

* Convenciones de arquitectura y estilos de código.
* Entorno de ejecución (`env/bin/python`) y gestión de dependencias.
* Reglas críticas de base de datos (SQLAlchemy 2.0 y migraciones de Alembic).
* Puntos de mejora técnica identificados y tareas prioritarias.

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.
