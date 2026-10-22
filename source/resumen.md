# 📦 Resumen Técnico del Backend (`source/`)

Este documento proporciona una referencia rápida sobre la arquitectura interna, componentes, modelos y flujo de datos dentro del módulo `source/` del proyecto **IterTrack**.

---

## 🏛️ 1. Estructura de Directorios

```text
source/
├── main.py                    # FastAPI: routers, SPA en /, /register y /map, y /assets
├── static/
│   └── isologo.png            # Favicon (GET /favicon.ico)
├── services/
│   ├── auth.py                # Registro, login, JWT y usuario actual (/auth)
│   ├── devices.py             # Ingesta por lotes con token de dispositivo (/devices)
│   └── tracking.py            # Endpoints autenticados de camiones y telemetría (/trucks)
├── models/
│   ├── __init__.py            # Exportación de modelos para SQLAlchemy y Alembic
│   ├── device.py              # Device y DeviceAssignment
│   ├── ingestion.py           # IngestedPoint y RejectedIngestPoint
│   ├── organization.py        # Modelo ORM Organization
│   ├── truck.py               # Modelos ORM Truck y TrackingPoint
│   └── user.py                # Modelo ORM User
├── schemas/
│   ├── __init__.py            # Exportación de esquemas Pydantic
│   ├── auth.py                # Esquemas de registro, respuesta de usuario y token
│   ├── ingestion.py           # Contrato de ingesta v1 (DeviceIngestBatch)
│   └── truck.py               # Validación y serialización: Truck, Location, TrackingPoint
└── database/
    ├── config.py              # Variables de entorno y ajustes centralizados (Pydantic Settings)
    └── database.py            # Motor SQLAlchemy, SessionLocal, Base declarativa y get_db()
```

---

## 🛣️ 2. Rutas y Endpoints

### Punto de Entrada (`source/main.py`)
* `GET /`, `GET /register` y `GET /map`: sirven `frontend/dist/index.html` (SPA React; React Router resuelve la ruta). El guard del cliente valida el token antes de consultar datos.
* `GET /assets/*`: archivos hasheados del build (CSS y JS).
* `GET /favicon.ico`: sirve `source/static/isologo.png` y no se incluye en OpenAPI.
* `GET /health`: estado del servicio, público.
* Si falta `frontend/dist/index.html`, las rutas de la SPA responden `503` con el comando para generar el build.
* Incluye `auth_router` (`/auth`), `tracking_router` (`/trucks`) y `devices_router` (`/devices`). La SPA se sirve sin autenticación HTTP; las llamadas a la API de camiones requieren Bearer JWT.

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

### Enrutador de Dispositivos (`source/services/devices.py` - Prefijo `/devices`)
| Método | Endpoint | Descripción | Auth |
|---|---|---|---|
| `POST` | `/devices/ingest` | Ingesta por lotes de telemetría; valida el contrato `v=1`, normaliza `recorded_at` a UTC y rechaza camiones inactivos. | Token de dispositivo |

El token del dispositivo es independiente del JWT humano y se guarda solo como hash SHA-256.

> **Autenticación y alcance:** Todos los endpoints `/trucks`, incluidos los `GET`, requieren Bearer JWT. Cada usuario pertenece a una organización y los camiones nuevos se asignan a ella; los listados se filtran por organización y las operaciones sobre camiones existentes verifican esa pertenencia. Los permisos basados en roles todavía no están implementados.

> **Persistencia:** Los endpoints obtienen una sesión con `db: Session = Depends(get_db)`; la conexión se configura en `source/database/config.py`.

---

## 🗄️ 3. Modelos de Base de Datos (`source/models/truck.py`)

Basados en la sintaxis moderna de **SQLAlchemy 2.0**:

### `Truck` (Tabla `trucks`)
* `id: Mapped[int]` (Primary Key).
* `plate: Mapped[str]` (Unique).
* `organization_id: Mapped[int]` (Foreign Key a `organizations.id`).
* `active: Mapped[bool]` (Estado del vehículo; por defecto `True`).
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
* `recorded_at: Mapped[datetime]` (Momento en que se midió la ubicación; con zona horaria).
* `received_at: Mapped[datetime]` (Momento en que el servidor recibió el punto).
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

## 🗺️ 5. Interfaz de Monitoreo (`frontend/`)

SPA en **React 19 + TypeScript + Vite**, compilada a `frontend/dist` y servida por FastAPI. El mapa usa **Leaflet 1.9** con **MapLibre GL** sobre mosaicos de **OpenStreetMap / OpenFreeMap**:

* **Mapa en vivo (`src/components/MapView.tsx`):** reconciliación de marcadores por camión y `flyTo` al seleccionar una unidad.
* **Orientación cenital (`src/lib/truckIcon.ts`):** ícono SVG del camión con faros y flecha de rumbo que rota con `transform: rotate(var(--heading))` según el *bearing*.
* **Movimiento (`src/lib/movement.ts`):** interpolación entre la posición anterior y la nueva con `requestAnimationFrame` para que el camión no salte entre pings.
* **Panel de telemetría (`TruckDetail`):** velocidad, rumbo, punto cardinal y último punto conocido.
* **Tarjetas inferiores (`SpeedBars`, `FleetDonuts`, `BottomCards`):** distribución de velocidades y estado de la flota.
* **Estado (`src/state/DashboardProvider.tsx`):** guard de sesión contra `/auth/me`, polling cada 3 s (`POLL_MS`) y carga del historial (`/trucks/{id}/iter`) al seleccionar un camión.
