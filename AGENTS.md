# 🤖 AGENTS.md - Guía e Instrucciones para Agentes de Inteligencia Artificial

Este documento define el contexto, las reglas arquitectónicas, los estándares de código y las restricciones de seguridad que **todo agente de IA** (Antigravity, Claude Code, Cursor, Copilot, etc.) debe seguir estrictamente al interactuar con el repositorio **IterTrack**.

---

## 📌 1. Visión General del Proyecto

* **Nombre:** IterTrack
* **Propósito:** Plataforma de rastreo y telemetría satelital GPS para camiones y flotas en tiempo real.
* **Componentes Principales:**
  1. **Backend:** API REST construida con **FastAPI** (`source/`).
  2. **Persistencia:** Base de datos relacional **PostgreSQL** administrada mediante **SQLAlchemy 2.0** y **Alembic** (`source/models/`, `alembic/`).
  3. **Simulador:** Script Python para generar desplazamientos y enviar coordenadas continuas (`scripts/simulate_trucks.py`).
  4. **Hardware Embebido:** Firmware C++ para microcontroladores **ESP32** con **PlatformIO** (ubicado en la rama `origin/IterTrack-Hardware`).

---

## 💻 2. Entorno de Ejecución y Dependencias

* **Ruta del Entorno Virtual:** `/home/octa/IterTrack/env`
* **Binarios que DEBES usar para ejecutar comandos:**
  * Python: `env/bin/python`
  * Uvicorn: `env/bin/uvicorn`
  * Alembic: `env/bin/alembic`
  * Pip: `env/bin/pip`
* **Regla:** Nunca asumas que las dependencias están en el Python global del sistema. Ejecuta siempre a través de `env/bin/...` o activando el entorno (`source env/bin/activate`).
* **Actualización de dependencias:** Si agregas una biblioteca, agrégala tanto al código como a `requirements.txt`.

---

## 🌿 3. Ramas y Flujo de Trabajo Git

* `main`: Rama de producción / código estable.
* `experiment/http`: Rama activa de desarrollo para el backend HTTP, base de datos y esquemas.
* `IterTrack-Hardware`: Rama dedicada exclusivamente al firmware ESP32 y código PlatformIO (`Iter-Hard/`).

---

## 🏛️ 4. Estándares de Arquitectura y Separación de Capas

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
   * Agrupados en `APIRouter` con prefijos y etiquetas claras (`tags=["trucks"]`).
   * Los endpoints deben responder con los códigos de estado HTTP semánticos correspondientes (`200`, `201`, `400`, `404`, etc.) usando `raise HTTPException(...)` en lugar de devolver diccionarios con `"error": ...` y estado `200 OK`.

---

## 🛡️ 5. Reglas Críticas de Seguridad y Secretos

1. **Nunca exponer secretos:**
   * **JAMÁS** escribas contraseñas reales, tokens o claves de base de datos en archivos rastreados por Git (`source/`, `alembic.ini.example`, etc.).
   * `.env` y `alembic.ini` están en `.gitignore`. Verifica siempre que tus cambios no intenten forzar su inclusión en Git.
   * Si agregas una nueva variable de configuración, regístrala con valores genéricos en [`.env.example`](./.env.example) y en `source/database/config.py`.
2. **Validación de entradas:**
   * Nunca confíes en los datos recibidos de clientes o módulos GPS externos. Valida tipos, formatos, longitudes y rangos numéricos.
3. **Prevención de Inyección:**
   * Utiliza siempre el ORM de SQLAlchemy o consultas parametrizadas. Nunca concatenes strings en consultas SQL.

---

## 🗄️ 6. Guía para Cambios en Base de Datos (Alembic)

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

## ⚠️ 7. Deuda Técnica Conocida y Tareas Prioritarias

Si estás realizando refactorizaciones o corrigiendo bugs en el proyecto, ten en cuenta los siguientes puntos pendientes:

* **Inconsistencia BD vs Memoria en `tracking.py`:**
  * El endpoint `POST /trucks` guarda en PostgreSQL mediante `db.commit()`.
  * Sin embargo, `PUT /{truck_id}/location`, `GET /{truck_id}/location`, `GET /trucks`, etc., aún utilizan los diccionarios en memoria `truck_db` y `current_location_db`.
  * **Objetivo:** Migrar todos los endpoints de `source/services/tracking.py` para consultar y persistir exclusivamente en la base de datos PostgreSQL utilizando la sesión `db: Session`.
* **Imports pendientes en `source/services/tracking.py`:**
  * La función `update_location` hace referencia a `Location` y `TrackingPoint` sin importarlos en el namespace (deben importarse desde `source.schemas` y `source.models`).
* **Manejo de Errores:**
  * Reemplazar las respuestas de error en formato `return {"error": "..."}` por excepciones nativas de FastAPI: `raise HTTPException(status_code=404, detail="...")`.
* **Validación de Coordenadas:**
  * Actualizar `source/schemas/truck.py` para que `lat` valide entre `-90.0` y `90.0` y `long` entre `-180.0` y `180.0`.

---

## 🧪 8. Comandos Útiles para Agentes

* **Verificar sintaxis e importaciones:**
  ```bash
  env/bin/python -m py_compile source/main.py
  env/bin/python -m py_compile source/services/tracking.py
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
