# 📦 Resumen Técnico del Backend (`source/`)

Este documento proporciona una referencia rápida sobre la arquitectura interna, componentes, modelos y flujo de datos dentro del módulo `source/` del proyecto **IterTrack**.

---

## 🏛️ 1. Estructura de Directorios

```text
source/
├── main.py                    # Instancia de FastAPI, inclusión de routers y vista /map
├── static/
│   └── map.html               # Interfaz web de monitoreo satelital en tiempo real (Leaflet / OSM)
├── services/
│   └── tracking.py            # Endpoints REST para camiones y telemetría (/trucks)
├── models/
│   ├── __init__.py            # Exportación de modelos para SQLAlchemy y Alembic
│   └── truck.py               # Modelos ORM: Truck y TrackingPoint
├── schemas/
│   ├── __init__.py            # Exportación de esquemas Pydantic
│   └── truck.py               # Validación y serialización: Truck, Location, TrackingPoint
└── database/
    ├── config.py              # Variables de entorno y ajustes centralizados (Pydantic Settings)
    ├── database.py            # Motor SQLAlchemy, SessionLocal, Base declarativa y get_db()
    └── basic_auth_users.py    # Esquemas base para usuarios y autenticación
```

---

## 🛣️ 2. Rutas y Endpoints

### Punto de Entrada (`source/main.py`)
* `GET /`: Mensaje de comprobación de salud del servicio.
* `GET /map`: Retorna `source/static/map.html` (`FileResponse`) para visualización web en vivo.
* Incluye el enrutador `tracking_router` con el prefijo `/trucks`.

### Enrutador de Telemetría (`source/services/tracking.py` - Prefijo `/trucks`)
| Método | Endpoint | Parámetros / Body | Descripción |
|---|---|---|---|
| `POST` | `/trucks` | `{ truck: Truck, location: Location }` | Registra un nuevo camión y su primera posición en BD. |
| `PUT` | `/trucks/{truck_id}/location` | `location: Location` | Agrega un nuevo punto de tracking al recorrido del camión. |
| `GET` | `/trucks/{truck_id}/location` | `truck_id: int` | Retorna el último punto registrado ordenado por timestamp descendente. |
| `GET` | `/trucks/{truck_id}/iter` | `truck_id: int` | Retorna los últimos 100 puntos del historial de recorrido. |
| `GET` | `/trucks` | — | Lista todos los camiones registrados en la base de datos. |
| `GET` | `/trucks/ids` | — | Lista simplificada con solo IDs y patentes. |

> **Nota:** Todos los endpoints interactúan directamente con PostgreSQL mediante la dependencia `db: Session = Depends(get_db)`.

---

## 🗄️ 3. Modelos de Base de Datos (`source/models/truck.py`)

Basados en la sintaxis moderna de **SQLAlchemy 2.0**:

### `Truck` (Tabla `trucks`)
* `id: Mapped[int]` (Primary Key).
* `plate: Mapped[str]` (Unique).
* `tracking_points: Mapped[list["TrackingPoint"]]` (Relación 1 a N con `TrackingPoint`, `back_populates="truck"`).

### `TrackingPoint` (Tabla `tracking_points`)
* `id: Mapped[int]` (Primary Key, autoincremental).
* `truck_id: Mapped[int]` (Foreign Key `trucks.id`).
* `lat: Mapped[float]` (Latitud geográfica).
* `long: Mapped[float]` (Longitud geográfica).
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
* **`TrackingPoint`:**
  * `truck_id: int`
  * `location: Location`
  * `timestamp: datetime` (Default `datetime.now`)

---

## 🗺️ 5. Interfaz de Monitoreo (`source/static/map.html`)

Frontend interactivo construido con **Leaflet 1.9** y mosaicos de **OpenStreetMap**:
* **Orientación cenital en tiempo real:** Icono SVG personalizado de camión con faros delanteros y flecha de rumbo que rota dinámicamente (`transform: rotate(...)`) mediante cálculo esférico de *bearing*.
* **Flechas direccionales adaptativas:** Muestra flechas sobre la línea de recorrido espaciadas en base a distancia visual de pantalla (`MIN_ESPACIADO_PIXELES = 85px`), aumentando en *zoom in* y sintetizándose en *zoom out*.
* **Panel de telemetría:** Indica patente, coordenadas en tiempo real, rumbo numérico y punto cardinal (ej. `137° SE`).
* **Seguimiento inteligente:** Checkbox para auto-centrado que se desactiva automáticamente si el usuario arrastra el mapa manualmente.
