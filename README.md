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
11. [Seguridad y Buenas Prácticas](#-seguridad-y-buenas-prácticas)
12. [Instrucciones para Agentes de IA](#-instrucciones-para-agentes-de-ia)
13. [Licencia](#-licencia)

---

## 🚀 Características

* **Registro y gestión de camiones:** Identificación única por ID y patente vehicular única.
* **Telemetría GPS en tiempo real:** Recepción continua de coordenadas, velocidad, rumbo y timestamp.
* **Monitoreo en vivo en mapa interactivo:** Visualización en tiempo real sobre OpenStreetMap y Leaflet (`/map`) con rotación de vehículo según rumbo (*bearing*), flechas direccionales adaptativas al zoom y seguimiento automático.
* **Historial de recorrido:** Almacenamiento y consulta de los últimos puntos geográficos transitados.
* **Autenticación OAuth2 + JWT:** Registro y login resueltos en el navegador (`/` y `/register`); todos los endpoints de camiones, tanto de lectura como de escritura, requieren token Bearer. Contraseñas hasheadas con bcrypt y tokens firmados con HS256.
* **Persistencia Robusta:** Modelos relacionales con SQLAlchemy 2.0 y control de versiones de esquema con Alembic sobre PostgreSQL.
* **Simulador integrado con ruta realista:** Script Python con un circuito cerrado de 13 km por Córdoba Capital (425 puntos) para pruebas de avance y orientación en tiempo real.
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
        MAP["Mapa en Vivo Leaflet (static/map.html)"]
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
├── requirements.txt               # Dependencias Python del proyecto
├── .gitignore                     # Filtro de exclusiones para Git
├── .env.example                   # Plantilla de variables de entorno (sin credenciales reales)
├── alembic.ini.example            # Plantilla de configuración para migraciones de Alembic
├── scripts/
│   ├── simulate_trucks.py         # Script para simular recorrido y envío de datos GPS
│   └── cordoba_route.json         # Coordenadas georreferenciadas de la ruta urbana de prueba
├── alembic/
│   ├── env.py                     # Configuración del entorno de migración de Alembic
│   ├── script.py.mako             # Template para generación de revisiones
│   └── versions/                  # Historial de migraciones de la base de datos
│       ├── abfa27c3f9e8_crear_tablas_trucks_y_tracking_points.py
│       └── 391c6b7b75c0_create_users_table.py
└── source/
    ├── main.py                    # Punto de entrada de la aplicación FastAPI (API y /map)
    ├── static/
    │   ├── login.html               # Página de login (enlace a /register)
    │   ├── register.html            # Formulario de registro con auto-login
    │   └── map.html               # Frontend interactivo con Leaflet, rumbo y telemetría
    ├── database/
    │   ├── config.py              # Carga de variables de entorno (DB, JWT)
    │   └── database.py            # Motor de conexión, SessionLocal y Base declarativa
    ├── models/
    │   ├── __init__.py
    │   ├── truck.py               # Modelos ORM: Truck y TrackingPoint
    │   └── user.py                # Modelo ORM: User
    ├── schemas/
    │   ├── __init__.py
    │   ├── truck.py               # Esquemas Pydantic: Truck, Location, TrackingPoint
    │   └── auth.py                # Esquemas Pydantic: UserCreate, UserResponse, Token
    └── services/
        ├── tracking.py            # Endpoints de la API (/trucks)
        └── auth.py                # Utilidades JWT + endpoints (/auth)
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
* **Cliente HTTP de pruebas:** [Requests](https://requests.readthedocs.io/).
* **Autenticación:** [python-jose](https://python-jose.readthedocs.io/) (JWT), [passlib](https://passlib.readthedocs.io/) + bcrypt.
* **Hardware:** [PlatformIO](https://platformio.org/) / C++ / ESP32 (Arduino framework).

---

## 📋 Requisitos Previos

1. **Python 3.12 o superior** instalado en el sistema.
2. **Servidor PostgreSQL** en ejecución local o remoto con una base de datos creada (ej. `itertrack`).
3. **Git** instalado.

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

---

## ▶️ Ejecución

Inicia el servidor de desarrollo con Uvicorn:

```bash
uvicorn source.main:app --reload --port 8000
```

El servidor quedará disponible en `http://127.0.0.1:8000`.

### 📖 Documentación Interactiva

Una vez iniciado el servidor, puedes interactuar directamente con los endpoints y el mapa desde el navegador:

* **Login:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/) (acceso al mapa; el enlace "Registrate" lleva a `/register`)
* **Mapa en Vivo (Leaflet):** [http://127.0.0.1:8000/map](http://127.0.0.1:8000/map) (la página valida la sesión y consulta la API con Bearer JWT)
* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🛰 Simulación de Telemetría

El repositorio incluye un simulador para verificar la recepción y visualización continua de telemetría en tiempo real. Antes de ejecutarlo, inicia el backend y registra una cuenta asociada a una organización. Configura `API_USER` y `API_PASSWORD` con las credenciales válidas de esa cuenta; el simulador inicia sesión en `/auth/login` y usa el token Bearer para enviar datos. Los camiones que registra quedan asociados a la organización de esa cuenta.

```bash
# El simulador lee API_USER y API_PASSWORD desde scripts/.env.
# Copiá la plantilla y completá con una cuenta demo local:
cp scripts/.env.example scripts/.env

# También podés pasarlas por entorno, con prioridad sobre el archivo:
export API_USER=demo
export API_PASSWORD=tu_clave_local

# Ejecución estándar (2 segundos por ping):
python scripts/simulate_trucks.py

# Simulación a mayor velocidad (ej. 1 segundo entre pings):
python scripts/simulate_trucks.py -i 1.0

# Asignar ID o patente personalizada:
python scripts/simulate_trucks.py --id 1 --plate "ABC123" -i 1.5
```

Si `API_USER` o `API_PASSWORD` no están definidas ni en el entorno ni en `.env`, el simulador aborta con un mensaje explícito en lugar de enviar telemetría sin autenticar.

### Características de la simulación:
1. **Ruta Urbana Realista:** Recorre un circuito cerrado de 13 km por avenidas de Córdoba Capital (Av. Colón, Costanera, Plaza España, Patio Olmos, etc.) cargado desde [`scripts/cordoba_route.json`](./scripts/cordoba_route.json) (425 puntos georreferenciados).
2. **Telemetría Completa:** Muestra en tiempo real el rumbo en grados (°), punto cardinal (N, SE, etc.), velocidad calculada en km/h y estado HTTP (`200 OK`).
3. **Bucle Continuo:** Al completar los 425 puntos, reinicia automáticamente la siguiente vuelta sin interrupciones.

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
| `GET` | `/` | Página de login (`static/login.html`) | — | — |
| `GET` | `/register` | Página de registro (`static/register.html`) | — | — |
| `GET` | `/map` | Página pública; el frontend valida la sesión antes de consultar la API | — | — |
| `GET` | `/favicon.ico` | Ícono de la pestaña del navegador (`static/isologo.png`) | — | — |
| `POST` | `/auth/register` | Registra un usuario; el JSON incluye `org_name` o `invitation_code` | Ver JSON de registro abajo | — |
| `POST` | `/auth/login` | Login OAuth2 (form-data) y devuelve JWT | `username` / `password` (form) | — |
| `GET` | `/auth/me` | Datos del usuario autenticado | — | 🔒 Bearer |
| `POST` | `/trucks` | Registra un nuevo camión y su punto inicial | Ver JSON abajo | 🔒 Bearer |
| `PUT` | `/trucks/{truck_id}/location` | Agrega un punto de ubicación al historial del camión | `{"lat": -31.416, "long": -64.183, "speed": 0, "heading": 0}` | 🔒 Bearer |
| `GET` | `/trucks/{truck_id}/location` | Obtiene el punto de tracking más reciente | — | 🔒 Bearer |
| `GET` | `/trucks/{truck_id}/iter` | Obtiene hasta 100 puntos, del más nuevo al más antiguo | — | 🔒 Bearer |
| `DELETE` | `/trucks/{truck_id}/iter` | Elimina los puntos de tracking del camión, no el camión | — | 🔒 Bearer |
| `GET` | `/trucks` | Lista los camiones de la organización del usuario autenticado | — | 🔒 Bearer |
| `GET` | `/trucks/ids` | Lista IDs y patentes de los camiones de la organización del usuario autenticado | — | 🔒 Bearer |

### Flujo de autenticación:

**En el navegador (camino principal):** abrí `http://127.0.0.1:8000/` e iniciá sesión, o seguí el enlace "Registrate" a `/register`; el registro inicia sesión automáticamente, guarda el token en el navegador y redirige a `/map`.

**Vía API (alternativa programática):**

1. **Registro:** `POST /auth/register` con usuario, email, nombre completo, contraseña y exactamente uno de `org_name` o `invitation_code` (la contraseña se persiste hasheada con bcrypt).
2. **Login:** `POST /auth/login` con `username` y `password` como *form-data*; devuelve `{"access_token": "...", "token_type": "bearer"}`.
3. **Uso del token:** incluir el header `Authorization: Bearer <access_token>` en las peticiones a los endpoints protegidos (🔒). El token expira según `ACCESS_TOKEN_EXPIRE_MINUTES` (60 min por defecto).

Ejemplo de registro creando una organización:

```json
{
  "username": "usuario",
  "email": "usuario@example.com",
  "full_name": "Nombre Apellido",
  "password": "<password>",
  "org_name": "Mi organización"
}
```

Para unirse a una organización existente, usa `invitation_code` en lugar de `org_name`. La API rechaza solicitudes que incluyan ambos campos o ninguno.

### Membresía y alcance de acceso

El registro crea una organización con `org_name` o asocia al usuario a una organización existente con `invitation_code`. Los camiones creados pertenecen a la organización del usuario autenticado; los listados se filtran por organización y los endpoints que consultan o modifican un camión verifican esa pertenencia. La membresía y el alcance de datos por organización están implementados; los permisos basados en roles siguen pendientes y se mantienen como trabajo futuro del producto.

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

## 🔒 Seguridad y Buenas Prácticas

1. **Gestión de Secretos:** 
   * **Nunca** subas archivos `.env` ni `alembic.ini` con contraseñas reales a Git. Ambos están protegidos en `.gitignore`.
   * Utiliza siempre los archivos `.example` como base para nuevos despliegues.
2. **Validación de Datos:**
   * Las coordenadas GPS deben restringirse en los esquemas Pydantic (`-90 <= lat <= 90` y `-180 <= long <= 180`).
3. **Autenticación:**
   * Implementada con OAuth2 Password Flow + JWT (HS256). Todos los endpoints `/trucks` (lectura y escritura) requieren Bearer Token; las páginas estáticas se sirven públicamente, pero `/map` valida la sesión en el navegador antes de mostrar los datos. `GET /auth/me` devuelve el usuario autenticado.
   * Las contraseñas nunca se almacenan en texto plano: se hashean con bcrypt antes de persistir en la tabla `users`.
   * `UserResponse` garantiza que `hashed_password` nunca se expone en las respuestas.
4. **Integración Continua:**
   * Cada `push` y cada pull request sobre `main` y `experiment/http` corre automáticamente `make check` y `make test` en GitHub Actions (`.github/workflows/ci.yml`).
   * El workflow crea el virtualenv `env/` que el `Makefile` espera; no requiere PostgreSQL porque los tests usan SQLite en memoria.
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
