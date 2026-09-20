# 🚚 IterTrack - GPS Tracking System

Sistema integral de rastreo y telemetría satelital GPS para flotas de camiones en tiempo real. Cuenta con un backend desarrollado en **FastAPI**, persistencia relacional en **PostgreSQL** mediante **SQLAlchemy 2.0** y **Alembic**, simulación de trayectorias y soporte para clientes de hardware embebido (**ESP32 / PlatformIO**).

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
* **Telemetría GPS en tiempo real:** Recepción continua de coordenadas (latitud, longitud, timestamp).
* **Historial de recorrido:** Almacenamiento y consulta de los últimos puntos geográficos transitados.
* **Persistencia Robusta:** Modelos relacionales con SQLAlchemy 2.0 y control de versiones de esquema con Alembic sobre PostgreSQL.
* **Simulador integrado:** Script en Python para emular camiones en movimiento transmitiendo coordenadas continuas al backend.
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
        Schemas["Pydantic Schemas (schemas/truck.py)"]
        ORM["SQLAlchemy Models (models/truck.py)"]
        DBCfg["Database Config & Engine (database/)"]
    end

    subgraph Storage["Persistencia"]
        PG[("PostgreSQL")]
        AL["Alembic Migrations"]
    end

    HW -->|HTTP POST / PUT JSON| API
    SIM -->|HTTP POST / PUT JSON| API
    API --> Router
    Router --> Schemas
    Router --> ORM
    ORM --> DBCfg
    DBCfg --> PG
    AL -.->|Control de Esquemas| PG
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
│   └── simulate_trucks.py         # Script para simular recorrido y envío de datos GPS
├── alembic/
│   ├── env.py                     # Configuración del entorno de migración de Alembic
│   ├── script.py.mako             # Template para generación de revisiones
│   └── versions/                  # Historial de migraciones de la base de datos
│       └── abfa27c3f9e8_crear_tablas_trucks_y_tracking_points.py
└── source/
    ├── main.py                    # Punto de entrada de la aplicación FastAPI
    ├── database/
    │   ├── config.py              # Carga de variables de entorno con Pydantic Settings
    │   ├── database.py            # Motor de conexión, SessionLocal y Base declarativa
    │   └── basic_auth_users.py    # Definición inicial para esquemas de autenticación
    ├── models/
    │   ├── __init__.py
    │   └── truck.py               # Modelos ORM: Truck y TrackingPoint
    ├── schemas/
    │   ├── __init__.py
    │   └── truck.py               # Esquemas Pydantic: Truck, Location, TrackingPoint
    └── services/
        └── tracking.py            # Controladores y endpoints de la API (/trucks)
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
```

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

Una vez iniciado el servidor, puedes interactuar directamente con los endpoints desde el navegador:

* **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🛰 Simulación de Telemetría

El repositorio incluye un simulador para verificar la recepción continua de coordenadas en tiempo real:

```bash
python scripts/simulate_trucks.py
```

Este script:
1. Registra un camión inicial (ID `1`, Patente `ABC123`) con coordenadas base.
2. Genera desplazamientos aleatorios cada 2 segundos.
3. Envía solicitudes HTTP `PUT` al backend actualizando la posición actual.

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

| Método | Endpoint | Descripción | Cuerpo de la Petición (Ejemplo) |
|---|---|---|---|
| `GET` | `/` | Comprobación de estado de la API (*Health check*) | — |
| `POST` | `/trucks` | Registra un nuevo camión y su punto inicial | Ver JSON abajo |
| `PUT` | `/trucks/{truck_id}/location` | Actualiza la ubicación actual del camión | `{"lat": -31.416, "long": -64.183}` |
| `GET` | `/trucks/{truck_id}/location` | Obtiene la última ubicación conocida | — |
| `GET` | `/trucks/{truck_id}/iter` | Obtiene el historial reciente (últimos 10 puntos) | — |
| `GET` | `/trucks` | Lista todos los camiones registrados | — |
| `GET` | `/trucks/ids` | Lista únicamente los IDs de los camiones | — |
| `GET` | `/trucks/plate/{plate}` | Busca un camión por su patente | — |

### Ejemplo de Payload para `POST /trucks`:

```json
{
  "truck": {
    "id": 1,
    "plate": "ABC123"
  },
  "location": {
    "lat": -31.4166867,
    "long": -64.1834193
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
   * La API no debe exponerse a producción sin implementar mecanismos de autenticación (API Keys para dispositivos de telemetría y Bearer JWT para administradores/usuarios).

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
