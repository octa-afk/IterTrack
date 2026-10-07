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
  4. **Visualización / Frontend:** Mapa interactivo en tiempo real con **OpenStreetMap** y **Leaflet** (`source/static/map.html`, servido en `/map`) con orientación cenital del vehículo, cálculo de rumbo y flechas adaptativas.
  5. **Simulador:** Script Python con ruta urbana realista de 13 km por Córdoba Capital (`scripts/simulate_trucks.py`, `scripts/cordoba_route.json`).
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
* `experiment/http`: Rama activa de desarrollo para el backend HTTP, base de datos y esquemas.
* `IterTrack-Hardware`: Rama dedicada exclusivamente al firmware ESP32 y código PlatformIO (`Iter-Hard/`).

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
  * Todos los endpoints de `source/services/tracking.py` (`POST /trucks`, `PUT /{truck_id}/location`, `GET /{truck_id}/location`, `GET /{truck_id}/iter`, `GET /trucks`, `GET /trucks/ids`) ya consultan y persisten exclusivamente en PostgreSQL mediante la sesión inyectada `db: Session = Depends(get_db)`.
* **Autenticación OAuth2 + JWT (Completada):**
  * Modelo ORM `User` en `source/models/user.py` (tabla `users` creada vía migración `391c6b7b75c0`).
  * `source/schemas/auth.py` y `source/services/auth.py` implementados: registro, login (OAuth2PasswordRequestForm), `/auth/me`, hashing bcrypt y tokens JWT HS256.
  * Configuración JWT centralizada en `source/database/config.py`: `SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` (60).
  * `auth_router` incluido en `source/main.py`.
  * Endpoints de escritura de `tracking.py` (`POST /trucks`, `PUT /{truck_id}/location`, `DELETE /{truck_id}/iter`) protegidos con `Depends(get_current_user)`. Los `GET` permanecen públicos para el mapa.
  * `bcrypt` fijado en `4.0.1` en `requirements.txt` por incompatibilidad de passlib 1.7.4 con bcrypt 5.x.
* **Manejo de Errores Semántico (Completado):**
  * `add_truck` ahora lanza `HTTPException(status_code=400, ...)` en duplicados.
* **Validación de Coordenadas (Completada):**
  * `source/schemas/truck.py` valida `lat` entre `-90` y `90` y `long` entre `-180` y `180` con `Field(ge=..., le=...)`.
* **Extensión de Telemetría (Opcional):**
  * Posibilidad de admitir un campo opcional `heading` (rumbo) o `speed` (velocidad) en `Location` si el hardware ESP32 con módulo GPS NMEA envía las sentencias `$GPRMC`.

---

## 8. Comandos Útiles para Agentes

* **Verificar sintaxis e importaciones:**
  ```bash
  env/bin/python -m py_compile source/main.py
  env/bin/python -m py_compile source/services/tracking.py
  env/bin/python -m py_compile source/services/auth.py
  env/bin/python -m py_compile source/models/user.py
  ```
* **Comprobar carga de configuración:**
  ```bash
  env/bin/python -c "from source.database.config import settings; print('Config OK')"
  ```
* **Iniciar servidor de desarrollo:**
  ```bash
  env/bin/uvicorn source.main:app --reload --port 8000
  ```
* **Ejecutar simulación de camiones:**
  ```bash
  env/bin/python scripts/simulate_trucks.py
  ```

---

## 9. Política de Testing (obligatoria)

* Todo endpoint nuevo o modificado debe incluir tests en `tests/` (pytest).
* Los tests usan SQLite en memoria con `dependency_overrides` de `get_db` y `get_current_user` (ver `tests/conftest.py`).
* Correr antes de terminar cualquier tarea: `make test` y `make check`.
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
