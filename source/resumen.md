# 📦 Resumen Técnico del Backend (`source/`)

Este documento proporciona una referencia rápida sobre la arquitectura interna, componentes, modelos y flujo de datos dentro del módulo `source/` del proyecto **IterTrack**.

---

## 🏛️ 1. Estructura de Directorios

```text
source/
├── main.py                    # FastAPI, routers y páginas /, /register, /map y /favicon.ico
├── static/
│   ├── login.html              # Página de login (GET /)
│   ├── register.html           # Página de registro (GET /register)
│   ├── map.html                # Interfaz de monitoreo en vivo (GET /map)
│   └── isologo.png             # Favicon (GET /favicon.ico)
├── services/
│   ├── auth.py                 # Registro, login, JWT y usuario actual (/auth)
│   └── tracking.py             # Endpoints autenticados de camiones y telemetría (/trucks)
├── models/
│   ├── __init__.py            # Exportación de modelos para SQLAlchemy y Alembic
│   ├── organization.py         # Modelo ORM Organization
│   ├── truck.py                # Modelos ORM Truck y TrackingPoint
│   └── user.py                 # Modelo ORM User
├── schemas/
│   ├── __init__.py            # Exportación de esquemas Pydantic
│   ├── auth.py                 # Esquemas de registro, respuesta de usuario y token
│   └── truck.py                # Validación y serialización: Truck, Location, TrackingPoint
└── database/
    ├── config.py              # Variables de entorno y ajustes centralizados (Pydantic Settings)
    ├── database.py            # Motor SQLAlchemy, SessionLocal, Base declarativa y get_db()
```

---

## 🛣️ 2. Rutas y Endpoints

### Punto de Entrada (`source/main.py`)
* `GET /`: Sirve `source/static/login.html`.
* `GET /register`: Sirve `source/static/register.html`.
* `GET /map`: Sirve `source/static/map.html`; la página valida el token en el navegador antes de consultar datos.
* `GET /favicon.ico`: Sirve `source/static/isologo.png` y no se incluye en OpenAPI.
* Incluye `auth_router` (`/auth`) y `tracking_router` (`/trucks`). Las páginas estáticas se sirven sin autenticación HTTP; las llamadas a la API de camiones requieren Bearer JWT.

### Enrutador de autenticación (`source/services/auth.py` - Prefijo `/auth`)
| Método | Endpoint | Descripción | Auth |
|---|---|---|---|
| `POST` | `/auth/register` | Registra un usuario y lo asocia a una organización | — |
| `POST` | `/auth/login` | Valida credenciales y devuelve un JWT | — |
| `GET` | `/auth/me` | Devuelve el usuario autenticado | Bearer |

El registro requiere exactamente uno de `org_name` (crear una organización) o `invitation_code` (unirse a una existente); ambos o ninguno se rechazan.

### Enrutador de Telemetría (`source/services/tracking.py` - Prefijo `/trucks`)
| Método | Endpoint | Parámetros / Body | Descripción |
|---|---|---|---|
| `POST` | `/trucks` | `{ truck: Truck, location: Location }` | Registra un nuevo camión y su primera posición en BD. |
| `PUT` | `/trucks/{truck_id}/location` | `location: Location` | Agrega un nuevo punto de tracking al recorrido del camión. |
| `GET` | `/trucks/{truck_id}/location` | `truck_id: int` | Retorna el punto más reciente, ordenado por `recorded_at` descendente. |
| `GET` | `/trucks/{truck_id}/iter` | `truck_id: int` | Retorna hasta 100 puntos, del más nuevo al más antiguo según `recorded_at`. |
| `DELETE` | `/trucks/{truck_id}/iter` | `truck_id: int` | Elimina los puntos de tracking; conserva el camión. |
| `GET` | `/trucks` | — | Lista los camiones de la organización del usuario autenticado. |
| `GET` | `/trucks/ids` | — | Lista IDs y patentes de los camiones de esa organización. |

> **Autenticación y alcance:** Todos los endpoints `/trucks`, incluidos los `GET`, requieren Bearer JWT. Cada usuario pertenece a una organización y los camiones nuevos se asignan a ella; los listados se filtran por organización y las operaciones sobre camiones existentes verifican esa pertenencia. Los permisos basados en roles todavía no están implementados.

> **Persistencia:** Los endpoints obtienen una sesión con `db: Session = Depends(get_db)`; la conexión se configura en `source/database/config.py`.

---

## 🗄️ 3. Modelos de Base de Datos (`source/models/truck.py`)

Basados en la sintaxis moderna de **SQLAlchemy 2.0**:

### `Truck` (Tabla `trucks`)
* `id: Mapped[int]` (Primary Key).
* `plate: Mapped[str]` (Unique).
* `organization_id: Mapped[int]` (Foreign Key a `organizations.id`).
* `tracking_points: Mapped[list["TrackingPoint"]]` (Relación 1 a N con `TrackingPoint`, `back_populates="truck"`).

### `Organization` y `User`
* `Organization` guarda el nombre y el código de invitación, y se relaciona con sus usuarios y camiones.
* `User` pertenece a una organización mediante `organization_id`; el modelo actual no define roles.

### `TrackingPoint` (Tabla `tracking_points`)
* `id: Mapped[int]` (Primary Key, autoincremental).
* `truck_id: Mapped[int]` (Foreign Key `trucks.id`).
* `lat: Mapped[float]` (Latitud geográfica).
* `long: Mapped[float]` (Longitud geográfica).
* `speed: Mapped[float]` (Velocidad).
* `heading: Mapped[float]` (Rumbo en grados).
* `timestamp: Mapped[datetime]` (Fecha y hora de registro, default `datetime.now`).
* `truck: Mapped["Truck"]` (Relación inversa hacia `Truck`).

---

## 📐 4. Esquemas de Validación (`source/schemas/truck.py`)

Definidos con **Pydantic v2**:

* **`Truck`:**
  * `id: int`
  * `plate: str`
* **`Location`:**
  * `lat: float`
  * `long: float`
  * `speed: float` (opcional en la solicitud; default `0`, mínimo `0`).
  * `heading: float` (opcional en la solicitud; default `0`, rango `0`–`360`).
* **`TrackingPoint`:**
  * `truck_id: int`
  * `location: Location`
  * `timestamp: datetime` (Default `datetime.now`)

---

## 🗺️ 5. Interfaz de Monitoreo (`source/static/map.html`)

Frontend interactivo construido con **Leaflet 1.9** y mosaicos de **OpenStreetMap**:
* **Orientación cenital en tiempo real:** Icono SVG personalizado de camión con faros delanteros y flecha de rumbo que rota dinámicamente (`transform: rotate(...)`) mediante cálculo esférico de *bearing*.
* **Flechas direccionales adaptativas:** Muestra flechas sobre la línea de recorrido espaciadas en base a distancia visual de pantalla (`MIN_ESPACIADO_PIXELES = 85px`), aumentando en *zoom in* y sintetizándose en *zoom out*.
* **Panel de telemetría:** Presenta velocidad y rumbo, además de los datos de ubicación del camión.
* **Seguimiento inteligente:** Checkbox para auto-centrado que se desactiva automáticamente si el usuario arrastra el mapa manualmente.
