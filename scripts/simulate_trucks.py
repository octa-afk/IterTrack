import argparse
import json
import math
import os
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import partial
from itertools import pairwise
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

import requests

SCRIPT_ENV_FILE = Path(__file__).resolve().parent / ".env"

# Cuánto esperar antes de reintentar una recuperación de token que ya falló.
# Sin esto, un camión tomado por hardware real golpearía los endpoints de
# administración en cada punto de telemetría.
RECOVERY_COOLDOWN = 30.0

# Cuánto espera en el lugar un camión que no puede planificar (API o ruteo
# caídos, destino sin coordenada) antes de volver a intentar. Arranca corto y se
# duplica hasta el tope: un corte de OSRM de una hora no golpea la API cada dos
# segundos, y mientras tanto el camión no inventa un recorrido que el mapa no
# muestra.
ESPERA_REINTENTO_INICIAL = 5.0
ESPERA_REINTENTO_MAXIMA = 60.0
# Separación máxima entre los puntos de una recta. Con sólo los extremos el
# camión saltaría de golpe hasta la parada.
PASO_RECTA_M = 30.0
# Una ruta más corta que esto es "ya estoy ahí": no hay tramo que recorrer.
RUTA_MINIMA_M = 10.0
ESTADOS_VIAJE_ABIERTO = ("planned", "in_progress")


def cargar_env_local(ruta: Path | None = None) -> None:
    """Load `scripts/.env` without overriding variables already in the environment."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    candidate = SCRIPT_ENV_FILE if ruta is None else ruta
    if candidate.is_file():
        load_dotenv(candidate)


# Loaded before the endpoint constants below, so `API_URL` and `AUTH_URL` in
# `scripts/.env` actually take effect.
cargar_env_local()

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/trucks")
AUTH_URL = os.getenv("AUTH_URL", "http://127.0.0.1:8000/auth/login")


def _api_root(url: str) -> str:
    """Derive the API root so device endpoints can be reached from API_URL."""
    return url[: -len("/trucks")] if url.endswith("/trucks") else url


DEVICES_URL = f"{_api_root(BASE_URL)}/devices"
INGEST_URL = f"{DEVICES_URL}/ingest"
# Simulated devices are named after this prefix so the simulator can recognise
# its own devices and never take over a real ESP32 by accident.
SIMULATED_DEVICE_PREFIX = os.getenv("SIMULATED_DEVICE_PREFIX", "SIM")

ROUTES_DIR = Path(__file__).resolve().parent
# Un circuito por camión: si todos comparten ruta, el mapa muestra tres
# marcadores en fila india por las mismas calles. Los tres existen en el repo,
# así que el simulador nunca sale a la red.
ROUTE_FILES = (
    "cordoba_route_norte_sur.json",  # Argüello / Plaza San Martín / Jardín
    "cordoba_route_norte.json",  # Cerro de las Rosas / Argüello
    "cordoba_route_sur.json",    # Jardín / Av. Cruz Roja
)
ROUTE_FILE = ROUTES_DIR / ROUTE_FILES[0]

HEADERS: dict[str, str] = {}


class StopSignal(Protocol):
    """Subset of `threading.Event` the simulation loop depends on.

    The loop only needs to know whether it was asked to stop, so it types
    against this shape and tests can inject their own doubles.
    """

    def is_set(self) -> bool: ...

    def wait(self, timeout: float | None = None) -> bool: ...


@dataclass(frozen=True)
class TruckConfig:
    truck_id: int
    plate: str
    route_offset: int
    route_file: str


# Cada camión de la demo lleva patente propia: con `ABC123-01/-02/-03` la tabla
# y la búsqueda por patente se vuelven adivinanzas. `TRUCK_PLATES` las cambia sin
# tocar código y la leen tanto el seed como el simulador, que si no divergen.
DEFAULT_TRUCK_PLATES = ("ABC123", "DEF456", "XYZ789")
DEFAULT_BASE_PLATE = "ABC123"


def truck_plates() -> tuple[str, ...]:
    """Patentes de la flota simulada, en orden de camión."""
    raw = os.getenv("TRUCK_PLATES", "").strip()
    if not raw:
        return DEFAULT_TRUCK_PLATES
    plates = tuple(part.strip().upper() for part in raw.split(",") if part.strip())
    if not plates:
        raise ValueError("TRUCK_PLATES no tiene ninguna patente válida.")
    return plates


def truck_route_file(index: int) -> str:
    """Circuito de un camión, en orden de índice dentro de la flota."""
    return ROUTE_FILES[index % len(ROUTE_FILES)]


def truck_phase(index: int, count: int, route_length: int) -> int:
    """Fase de un camión dentro de su circuito.

    Con un circuito por camión cada uno arranca al principio del suyo. Cuando
    hay más camiones que circuitos, los que comparten ruta se reparten la vuelta
    para no viajar pegados.
    """
    route = truck_route_file(index)
    sharing = [other for other in range(count) if truck_route_file(other) == route]
    return route_offset(route_length, sharing.index(index), len(sharing))


def build_truck_configs(
    base_id: int,
    base_plate: str,
    count: int,
    route_length: int | None = None,
    plates: Sequence[str] | None = None,
) -> list[TruckConfig]:
    """Build deterministic identities and route offsets for the workers.

    `plates` fija la patente de cada camión. Si la lista se queda corta, o no
    viene, se cae al esquema `<base_plate>-NN` para no romper los despliegues
    que no configuraron una flota propia.
    """
    if count < 1:
        raise ValueError("count must be at least 1")

    pool = tuple(plates or ())
    configs: list[TruckConfig] = []
    for index in range(count):
        route_file = truck_route_file(index)
        compartido = sum(
            1 for other in range(count) if truck_route_file(other) == route_file
        )
        offset = 0
        if compartido > 1:
            # Sólo hace falta medir la ruta cuando varios camiones la comparten.
            length = (
                route_length
                if route_length is not None
                else len(cargar_ruta(route_file))
            )
            offset = truck_phase(index, count, length)
        configs.append(
            TruckConfig(
                truck_id=base_id + index,
                plate=(
                    pool[index]
                    if index < len(pool)
                    else base_plate
                    if count == 1
                    else f"{base_plate}-{index + 1:02d}"
                ),
                route_offset=offset,
                route_file=route_file,
            )
        )
    return configs


def route_offset(route_length: int, truck_index: int, truck_count: int) -> int:
    """Return an evenly distributed, valid phase offset for a route."""
    if route_length < 1:
        raise ValueError("route_length must be at least 1")
    if truck_count < 1 or not 0 <= truck_index < truck_count:
        raise ValueError("truck_index must be within truck_count")
    if truck_count > route_length:
        return truck_index % route_length
    return truck_index * route_length // truck_count


def rotate_route(route: list, offset: int) -> list:
    """Return a route beginning at offset without mutating the source route."""
    if not route:
        return []
    offset %= len(route)
    return route[offset:] + route[:offset]

def _login(user_var: str, password_var: str, etiqueta: str) -> dict[str, str]:
    """Authenticate with a pair of environment variables and return the headers."""
    username = os.getenv(user_var)
    password = os.getenv(password_var)
    if not username or not password:
        print(f"⚠️ Faltan {user_var} y {password_var}: definilas en el entorno o en scripts/.env.")
        return {}
    try:
        response = requests.post(
            AUTH_URL,
            data={"username": username, "password": password},
            timeout=5,
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"🔑 Login OK como '{username}' ({etiqueta}).")
            return {"Authorization": f"Bearer {token}"}
        print(f"⚠️ Login {etiqueta} falló ({response.status_code}): {response.text}")
    except requests.RequestException as e:
        print(f"⚠️ Error de conexión en login {etiqueta}: {e}")
    return {}


def autenticar_admin() -> dict:
    """Login de administración con ADMIN_API_USER / ADMIN_API_PASSWORD."""
    return _login("ADMIN_API_USER", "ADMIN_API_PASSWORD", "admin")

def calcular_rumbo(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula el rumbo (bearing) en grados (0-360) entre dos puntos geográficos."""
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360

def punto_cardinal(grados: float) -> str:
    """Devuelve la abreviación del punto cardinal para un ángulo en grados."""
    direcciones = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
    idx = round(grados / 45) % 8
    return direcciones[idx]

def calcular_distancia_metros(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula la distancia Haversine en metros entre dos puntos geográficos."""
    r = 6371000  # Radio terrestre en metros
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def espera_y_velocidad(
    dist_metros: float, intervalo_minimo: float, objetivo_kmh: float
) -> tuple[float, float]:
    """Espera entre puntos y velocidad reportada para un tramo de la ruta.

    Los puntos de la ruta no están espaciados de forma uniforme: con una
    cadencia fija, un tramo de 162 m implica 293 km/h y el panel dibuja un
    límite de 90. Esperar en proporción a la distancia mantiene la velocidad
    por debajo del objetivo, y el intervalo mínimo evita que los tramos cortos
    martillen la API.
    """
    if dist_metros <= 0:
        return intervalo_minimo, 0.0
    metros_por_segundo = max(objetivo_kmh, 0.1) / 3.6
    espera = max(intervalo_minimo, dist_metros / metros_por_segundo)
    return espera, dist_metros / espera * 3.6


def espera_hacia_el_siguiente(
    ruta, indice: int, intervalo_minimo: float, objetivo_kmh: float, bucle: bool = True
) -> float:
    """Segundos a esperar después de emitir el punto `indice`.

    La espera pertenece al tramo que el camión recorre a continuación
    (`indice -> indice + 1`), no al que acaba de dejar atrás. Esperar el tramo
    ya recorrido desplaza el pacing un punto: cada tramo viaja con la espera
    del anterior y un tramo de 160 m precedido por uno de 20 m se recorre en
    2 s (≈290 km/h), que es justo lo que este cálculo evita.

    Con `bucle=True` el circuito se recorre en bucle y el último punto enlaza
    con el primero. Una ruta de OSRM es de ida: al llegar al destino no hay
    tramo siguiente que esperar.
    """
    if not bucle and indice >= len(ruta) - 1:
        return 0.0
    actual = ruta[indice]
    siguiente = ruta[(indice + 1) % len(ruta)]
    dist = calcular_distancia_metros(actual[0], actual[1], siguiente[0], siguiente[1])
    espera, _ = espera_y_velocidad(dist, intervalo_minimo, objetivo_kmh)
    return espera


def interpolar(desde, hasta, paso_m: float = PASO_RECTA_M) -> list[list[float]]:
    """Recta de `desde` a `hasta`, extremos incluidos, con un punto cada `paso_m`."""
    distancia = calcular_distancia_metros(desde[0], desde[1], hasta[0], hasta[1])
    pasos = max(1, math.ceil(distancia / paso_m))
    return [
        [
            desde[0] + (hasta[0] - desde[0]) * k / pasos,
            desde[1] + (hasta[1] - desde[1]) * k / pasos,
        ]
        for k in range(pasos + 1)
    ]


def longitud_m(puntos) -> float:
    """Largo de un recorrido sumando sus tramos."""
    return sum(
        calcular_distancia_metros(a[0], a[1], b[0], b[1]) for a, b in pairwise(puntos)
    )


def indice_mas_cercano(puntos, punto) -> int:
    """Índice del punto del recorrido más cercano a `punto`."""
    return min(
        range(len(puntos)),
        key=lambda i: calcular_distancia_metros(
            puntos[i][0], puntos[i][1], punto[0], punto[1]
        ),
    )


def cargar_ruta(route_file: str | None = None):
    """Carga los puntos de un circuito; sin argumento, el del primer camión."""
    path = ROUTES_DIR / route_file if route_file else ROUTE_FILE
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    else:
        # Fallback a circuito básico si el archivo no estuviese presente
        return [
            [-31.415118, -64.205147],
            [-31.413241, -64.185210],
            [-31.421500, -64.173200],
            [-31.430000, -64.185500],
            [-31.419500, -64.188500],
            [-31.415118, -64.205147]
        ]

def registrar_camion(
    truck_id: int,
    plate: str,
    headers=None,
):
    """Registra el camión si aún no existe. El alta no envía ubicación."""
    try:
        response = requests.post(
            BASE_URL,
            json={"id": truck_id, "plate": plate},
            headers=HEADERS if headers is None else headers,
            timeout=5
        )
        if response.status_code in (200, 201):
            print(f"✅ Camión #{truck_id} ({plate}) registrado con éxito.")
        else:
            # Si ya existía, la API devuelve error o 200 con mensaje
            data = response.json() if response.headers.get("content-type") == "application/json" else response.text
            print(f"ℹ️ Info registro camión #{truck_id}: {data}")  # noqa: RUF001
    except requests.RequestException as e:
        print(f"⚠️ Error conectando al servidor en {BASE_URL}: {e}")

def limpiar_recorrido(truck_id: int, headers=None):
    """Borra todo el recorrido registrado del camión llamando a DELETE /trucks/{id}/iter."""
    try:
        response = requests.delete(
            f"{BASE_URL}/{truck_id}/iter",
            headers=HEADERS if headers is None else headers,
            timeout=5,
        )
        if response.status_code == 204:
            print(f"🗑️ Recorrido del camión #{truck_id} borrado correctamente.")
        else:
            print(f"⚠️ No se pudo borrar el recorrido: {response.status_code}")
    except requests.RequestException as e:
        print(f"⚠️ Error al borrar recorrido: {e}")

def _renovar_jwt_admin(headers: dict) -> bool:
    """Pide un JWT de admin nuevo y lo deja en `headers`.

    El dict es el mismo para todos los hilos del worker: se actualiza en el
    lugar y la renovación de uno le sirve a los demás.
    """
    renovado = autenticar_admin()
    if not renovado:
        return False
    headers.update(renovado)
    return True


def _pedir_como_admin(metodo: str, url: str, headers: dict, **kwargs):
    """Request de administración que sobrevive al vencimiento del JWT.

    El JWT dura `ACCESS_TOKEN_EXPIRE_MINUTES` (60 por defecto) y el worker corre
    días. Sin renovarlo, a la hora de arrancar cada consulta de viajes respondía
    401 y el camión se quedaba en el circuito fijo mientras el mapa dibujaba la
    ruta del viaje.
    """
    enviar = getattr(requests, metodo)
    respuesta = enviar(url, headers=headers, **kwargs)
    if respuesta.status_code == 401 and _renovar_jwt_admin(headers):
        respuesta = enviar(url, headers=headers, **kwargs)
    return respuesta


def reiniciar_viaje(truck_id: int, headers=None):
    """Deja el viaje abierto del camión sin paradas hechas, para la corrida nueva.

    Sin esto el camión arranca en la parada 1 con las paradas 2 y 3 marcadas de
    la corrida anterior, y la ruta se dibuja hacia la última. Al reiniciar la
    simulación el recorrido es nuevo: el progreso del viaje también.
    """
    auth = HEADERS if headers is None else headers
    try:
        listado = _pedir_como_admin(
            "get",
            f"{_api_root(BASE_URL)}/trips",
            auth,
            params={"truck_id": truck_id},
            timeout=5,
        )
        if listado.status_code != 200:
            print(
                f"⚠️ No se pudieron listar los viajes del camión #{truck_id}: "
                f"{listado.status_code}"
            )
            return
        abiertos = [
            viaje
            for viaje in listado.json()
            if viaje.get("status") in ESTADOS_VIAJE_ABIERTO
        ]
        if not abiertos:
            return
        viaje = abiertos[0]
        response = _pedir_como_admin(
            "post",
            f"{_api_root(BASE_URL)}/trips/{viaje['id']}/reset",
            auth,
            timeout=5,
        )
        if response.status_code == 200:
            print(
                f"🔄 Viaje #{viaje['id']} del camión #{truck_id} reiniciado: "
                "todas las paradas quedaron pendientes."
            )
        else:
            print(
                f"⚠️ No se pudo reiniciar el viaje #{viaje['id']}: "
                f"{response.status_code}"
            )
    except requests.RequestException as e:
        print(f"⚠️ Error al reiniciar el viaje del camión #{truck_id}: {e}")


def renovar_viaje(truck_id: int, headers=None) -> bool:
    """Reabre el último viaje terminado del camión para que siga habiendo ruta.

    Los viajes se cierran solos: `trip_progress` marca la última parada como
    entregada y el viaje queda `done`. Desde ahí `GET /trips/{id}/route` responde
    409 y el mapa no tiene nada que dibujar, aunque el camión siga reportando.
    Reabrir ese mismo viaje (sin crear filas) devuelve la ruta al mapa y al
    simulador, que así no se queda recorriendo el circuito fijo.

    No toca nada si el camión ya tiene un viaje abierto: reabrir un `done` viejo
    dejaría dos viajes abiertos para el mismo camión.
    """
    auth = HEADERS if headers is None else headers
    try:
        listado = _pedir_como_admin(
            "get",
            f"{_api_root(BASE_URL)}/trips",
            auth,
            params={"truck_id": truck_id},
            timeout=5,
        )
        if listado.status_code != 200:
            return False
        viajes = listado.json()
    except (requests.RequestException, ValueError):
        return False

    if any(viaje.get("status") in ESTADOS_VIAJE_ABIERTO for viaje in viajes):
        return False

    terminados = [viaje for viaje in viajes if viaje.get("status") == "done"]
    if not terminados:
        return False
    viaje = max(terminados, key=lambda v: v.get("id", 0))

    try:
        response = _pedir_como_admin(
            "post",
            f"{_api_root(BASE_URL)}/trips/{viaje['id']}/reset",
            auth,
            timeout=5,
        )
    except requests.RequestException as e:
        print(f"⚠️ Error al renovar el viaje #{viaje['id']} del camión #{truck_id}: {e}")
        return False
    if response.status_code != 200:
        print(
            f"⚠️ No se pudo renovar el viaje #{viaje['id']} del camión "
            f"#{truck_id}: {response.status_code}"
        )
        return False
    print(
        f"♻️ Viaje #{viaje['id']} del camión #{truck_id} reabierto: vuelve a "
        "tener ruta hasta la primera parada."
    )
    return True


def listar_viajes(truck_id: int, headers=None) -> list[dict] | None:
    """Viajes del camión, el de salida más reciente primero.

    Devuelve `None` si la API no respondió: para el llamador no es lo mismo
    "no tiene viajes" que "no sé qué viajes tiene".
    """
    try:
        respuesta = _pedir_como_admin(
            "get",
            f"{_api_root(BASE_URL)}/trips",
            HEADERS if headers is None else headers,
            params={"truck_id": truck_id},
            timeout=5,
        )
        if respuesta.status_code != 200:
            return None
        viajes = respuesta.json()
    except (requests.RequestException, ValueError):
        return None
    return viajes if isinstance(viajes, list) else None


@dataclass(frozen=True)
class Ruta:
    """Respuesta de `GET /trips/{id}/route`: el código HTTP y la geometría.

    `estado` es `None` cuando no hubo respuesta (timeout, conexión caída).
    """

    estado: int | None
    puntos: list[list[float]] = field(default_factory=list)


def pedir_ruta(viaje_id: int, headers=None) -> Ruta:
    """Ruta por calles hasta la próxima parada del viaje: la que dibuja el mapa."""
    try:
        respuesta = _pedir_como_admin(
            "get",
            f"{_api_root(BASE_URL)}/trips/{viaje_id}/route",
            HEADERS if headers is None else headers,
            timeout=20,
        )
        if respuesta.status_code != 200:
            return Ruta(respuesta.status_code)
        geometry = respuesta.json().get("geometry") or []
        return Ruta(200, [[float(lat), float(lng)] for lat, lng in geometry])
    except (requests.RequestException, TypeError, ValueError):
        return Ruta(None)


@dataclass(frozen=True)
class Objetivo:
    """Lo que le toca al camión según su viaje abierto.

    `proxima` es la parada que evalúa el progreso automático: la primera, por
    `seq`, que no está entregada (`pending` o `arrived`). `destino` es a la que
    apunta la ruta del mapa: la primera `pending` con coordenada. Coinciden
    salvo cuando el camión ya llegó a una parada: ahí el mapa dibuja el tramo a
    la siguiente.
    """

    viaje_id: int | None = None
    proxima: dict | None = None
    destino: dict | None = None


def objetivo_del_camion(viajes: Sequence[dict]) -> Objetivo:
    """Lee del listado de viajes qué le toca al camión ahora.

    Replica las reglas de `trip_progress._next_pending_stop` y de
    `GET /trips/{id}/route` para que el simulador decida lo mismo que el
    progreso automático y que el mapa.
    """
    abiertos = [v for v in viajes if v.get("status") in ESTADOS_VIAJE_ABIERTO]
    if not abiertos:
        return Objetivo()
    # La API los lista por salida, la más reciente primero: es el mismo viaje
    # que mueve el progreso automático.
    viaje = abiertos[0]
    paradas = sorted(viaje.get("stops") or [], key=lambda parada: parada.get("seq", 0))
    proxima = next(
        (p for p in paradas if p.get("status") in ("pending", "arrived")), None
    )
    destino = next(
        (
            p
            for p in paradas
            if p.get("status") == "pending"
            and p.get("lat") is not None
            and p.get("lng") is not None
        ),
        None,
    )
    return Objetivo(viaje_id=viaje.get("id"), proxima=proxima, destino=destino)


def sigue_el_tramo(inicial: Objetivo, actual: Objetivo) -> bool:
    """El tramo hacia `inicial.destino` todavía es el que dibuja el mapa.

    Llegar a esa parada no lo cambia: el camión termina de acercarse. Sí lo
    cambia que se entregue antes de terminar el tramo (pasó cerca y se alejó),
    que el viaje se reinicie o que lo reemplace otro: seguir la geometría vieja
    manda al camión a un lugar que el mapa ya no muestra.
    """
    if inicial.destino is None or actual.viaje_id != inicial.viaje_id:
        return False
    parada_id = inicial.destino.get("id")
    if actual.destino is not None and actual.destino.get("id") == parada_id:
        return True
    return (
        actual.proxima is not None
        and actual.proxima.get("id") == parada_id
        and actual.proxima.get("status") == "arrived"
    )


def sigue_en_la_parada(inicial: Objetivo, actual: Objetivo) -> bool:
    """El camión todavía no salió del radio de la parada a la que llegó."""
    return (
        actual.viaje_id == inicial.viaje_id
        and inicial.proxima is not None
        and actual.proxima is not None
        and actual.proxima.get("id") == inicial.proxima.get("id")
        and actual.proxima.get("status") == "arrived"
    )


def sin_viaje_abierto(_inicial: Objetivo, actual: Objetivo) -> bool:
    """Vale mientras el camión siga sin viaje que hacer."""
    return actual.viaje_id is None


def listar_dispositivos(headers=None):
    """Return the devices visible to the caller, or None when the request fails."""
    try:
        response = requests.get(
            DEVICES_URL,
            headers=HEADERS if headers is None else headers,
            timeout=5,
        )
    except requests.RequestException as e:
        print(f"⚠️ Error al listar dispositivos: {e}")
        return None
    if response.status_code != 200:
        print(f"⚠️ No se pudieron listar dispositivos ({response.status_code}).")
        return None
    return response.json()


def _dispositivo_que_ocupa(dispositivos, truck_id):
    for device in dispositivos:
        assignment = device.get("assignment")
        if assignment and assignment.get("truck_id") == truck_id:
            return device
    return None


def _dispositivo_por_identificador(dispositivos, identifier):
    for device in dispositivos:
        if device.get("identifier") == identifier:
            return device
    return None


def _post_dispositivo(url, headers=None, payload=None):
    return requests.post(
        url,
        headers=HEADERS if headers is None else headers,
        json=payload,
        timeout=5,
    )


def _token_de(response):
    if response.status_code not in (200, 201):
        return None
    try:
        return response.json().get("token")
    except ValueError:
        return None


def _aprovisionar(identifier: str, truck_id: int, admin_headers) -> str | None:
    try:
        response = _post_dispositivo(
            DEVICES_URL, admin_headers, {"identifier": identifier, "truck_id": truck_id}
        )
    except requests.RequestException as e:
        print(f"⚠️ Error al aprovisionar '{identifier}': {e}")
        return None
    return _token_de(response)


def _rotar_token(device_id: int, admin_headers) -> str | None:
    try:
        response = _post_dispositivo(
            f"{DEVICES_URL}/{device_id}/token/rotate", admin_headers
        )
    except requests.RequestException as e:
        print(f"⚠️ Error al rotar el token del dispositivo {device_id}: {e}")
        return None
    return _token_de(response)


def _reasignar(device_id: int, truck_id: int, admin_headers) -> bool:
    try:
        response = _post_dispositivo(
            f"{DEVICES_URL}/{device_id}/reassign", admin_headers, {"truck_id": truck_id}
        )
    except requests.RequestException as e:
        print(f"⚠️ Error al reasignar el dispositivo {device_id}: {e}")
        return False
    return response.status_code == 200


def _revocar(device_id: int, admin_headers) -> bool:
    try:
        response = _post_dispositivo(f"{DEVICES_URL}/{device_id}/revoke", admin_headers)
    except requests.RequestException as e:
        print(f"⚠️ Error al revocar el dispositivo {device_id}: {e}")
        return False
    return response.status_code == 200


def _reaprovisionar_dispositivo(truck_id: int, admin_headers: dict) -> str | None:
    """Recovery entry: renew the admin JWT, then re-provision the device.

    El JWT de administración dura `ACCESS_TOKEN_EXPIRE_MINUTES` y el worker lo
    obtiene una sola vez al arrancar. Sin este re-login, la recuperación que
    dispara el reset diario de la demo (que borra los dispositivos) responde
    401 y la flota queda congelada hasta reiniciar el contenedor: el token del
    dispositivo ya no vale y no hay credencial válida para pedir uno nuevo.
    """
    _renovar_jwt_admin(admin_headers)
    return preparar_dispositivo(truck_id, admin_headers)


def preparar_dispositivo(truck_id: int, admin_headers=None, force: bool = False) -> str | None:
    """Return a token for a simulated device on `truck_id`, or None to skip it.

    The simulator never removes a device it did not create unless `force` is
    set, so a real ESP32 keeps its truck. Devices it owns are identified by
    `SIMULATED_DEVICE_PREFIX`.
    """
    identifier = f"{SIMULATED_DEVICE_PREFIX}-{truck_id:03d}"
    dispositivos = listar_dispositivos(admin_headers)
    if dispositivos is None:
        return None

    ocupante = _dispositivo_que_ocupa(dispositivos, truck_id)
    if ocupante is not None and ocupante.get("identifier") != identifier:
        if not force:
            print(
                f"⏭️ Camión #{truck_id} ocupado por '{ocupante.get('identifier')}' "
                "(hardware real): se saltea. Usá --force para revocarlo."
            )
            return None
        print(
            f"⚠️ --force: revocando '{ocupante.get('identifier')}' del camión #{truck_id}. "
            "Vas a tener que volver a aprovisionar ese ESP32."
        )
        if not _revocar(ocupante["id"], admin_headers):
            return None
        dispositivos = listar_dispositivos(admin_headers)
        if dispositivos is None:
            return None

    nuestro = _dispositivo_por_identificador(dispositivos, identifier)
    if nuestro is None:
        token = _aprovisionar(identifier, truck_id, admin_headers)
        if token is None:
            print(f"⛔ No se pudo aprovisionar '{identifier}' en el camión #{truck_id}.")
        return token

    asignacion = nuestro.get("assignment")
    if asignacion is None or asignacion.get("truck_id") != truck_id:
        if not _reasignar(nuestro["id"], truck_id, admin_headers):
            print(f"⛔ No se pudo reasignar '{identifier}' al camión #{truck_id}.")
            return None
    return _rotar_token(nuestro["id"], admin_headers)


def enviar_ingesta(
    token: str,
    lat: float,
    long: float,
    speed: float,
    heading: float,
    recorded_at: datetime,
    sequence: int = 1,
    batch_id: str | None = None,
    on_unauthorized: Callable[[], str | None] | None = None,
) -> bool:
    """Send one measurement through the same endpoint a real ESP32 uses.

    Un 401 significa que el token del dispositivo dejó de valer: un reset de la
    demo recrea los dispositivos y rotar un token invalida el anterior. Si
    ``on_unauthorized`` devuelve uno nuevo, el punto se reintenta una sola vez,
    igual que el camino de usuario cuando vence el JWT. Sin eso el worker queda
    en bucle de 401 y la flota se congela.
    """
    payload: dict[str, Any] = {
        "batch_id": batch_id or str(uuid4()),
        "points": [
            {
                "sequence": sequence,
                "lat": lat,
                "long": long,
                "speed": speed,
                "heading": heading,
                "recorded_at": recorded_at.isoformat(),
            }
        ],
    }
    def enviar(autenticacion: str):
        return requests.post(
            INGEST_URL,
            json=payload,
            headers={"Authorization": f"Bearer {autenticacion}"},
            timeout=5,
        )

    try:
        response = enviar(token)
        if response.status_code == 401 and on_unauthorized is not None:
            renovado = on_unauthorized()
            if renovado:
                response = enviar(renovado)
    except requests.RequestException as e:
        print(f"⚠️ Error al enviar ingesta: {e}")
        return False
    if response.status_code != 200:
        print(f"⚠️ Ingesta rechazada ({response.status_code}): {response.text}")
        return False
    results = response.json().get("results") or []
    rechazados = [result for result in results if result.get("status") != "accepted"]
    if rechazados:
        print(f"⚠️ Ingesta con puntos rechazados: {rechazados}")
        return False
    return True


def constructor_de_sender(
    token: str, on_unauthorized: Callable[[], str | None] | None = None
):
    """Bind a device token to the sender contract the route loop expects.

    Cuando ``on_unauthorized`` devuelve un token nuevo, se guarda para los
    puntos siguientes: una recuperación cuesta una rotación, no una por punto.
    Si la recuperación falla no se reintenta hasta pasar ``RECOVERY_COOLDOWN``,
    para que un camión tomado por hardware real no golpee la API sin pausa.
    """
    secuencia = {"n": 0}
    estado: dict[str, Any] = {"token": token, "ultimo_intento": -RECOVERY_COOLDOWN}

    def renovar() -> str | None:
        if monotonic() - estado["ultimo_intento"] < RECOVERY_COOLDOWN:
            return None
        nuevo = on_unauthorized() if on_unauthorized is not None else None
        # Un éxito habilita el intento siguiente de inmediato: el cooldown es
        # para no golpear la API cuando la recuperación no da token, no para
        # castigar a dos resets seguidos.
        estado["ultimo_intento"] = -RECOVERY_COOLDOWN if nuevo else monotonic()
        if nuevo:
            estado["token"] = nuevo
        return nuevo

    def enviar(lat, lon, velocidad, rumbo, medido_en) -> bool:
        secuencia["n"] += 1
        if on_unauthorized is None:
            return enviar_ingesta(
                estado["token"], lat, lon, velocidad, rumbo, medido_en,
                sequence=secuencia["n"],
            )
        return enviar_ingesta(
            estado["token"], lat, lon, velocidad, rumbo, medido_en,
            sequence=secuencia["n"], on_unauthorized=renovar,
        )

    return enviar


def simular_ruta(
    truck_id: int,
    plate: str,
    intervalo: float,
    stop_event: StopSignal | None = None,
    phase_offset: int = 0,
    admin_headers=None,
    sender=None,
    objetivo_kmh: float = 55.0,
    route_file: str | None = None,
):
    """Conduce el camión hacia donde el mapa dice que va, emitiendo por `sender`.

    La telemetría solo entra por `POST /devices/ingest`, así que `sender` es
    obligatorio: es el contrato que arma `constructor_de_sender` con el token
    del dispositivo. No existe camino alternativo con credenciales humanas.

    Con credenciales de admin el camión hace su viaje: la ruta de
    `GET /trips/{id}/route` hasta la próxima parada, la misma que dibuja el mapa
    (o la recta punteada, si no hay proveedor de ruteo). Antes de cada punto
    revisa que el viaje siga igual y, si cambió, pide la ruta nueva en vez de
    terminar la vieja. Si no puede planificar, espera en el lugar: nunca se va a
    un recorrido que el mapa no muestra. El circuito fijo queda para cuando no
    tiene viaje que hacer.
    """
    if sender is None:
        raise ValueError("simular_ruta necesita un sender de dispositivo")

    circuito = rotate_route(cargar_ruta(route_file), phase_offset)
    print(
        f"\n🚚 Camión #{truck_id} ({plate}) — circuito "
        f"{route_file or ROUTE_FILES[0]}: {len(circuito)} puntos"
    )
    print(
        f"⏱️ Intervalo mínimo: {intervalo}s | velocidad objetivo: {objetivo_kmh:.0f} km/h"
        f" | API: {DEVICES_URL}\n"
    )

    if stop_event is None:
        stop_event = Event()

    ultimo: list[float] | None = None
    ultimo_rumbo = 0.0
    # Lo último que recorrió hacia una parada: al llegar a la última, el camión
    # sale de su radio volviendo por ahí.
    ultimo_tramo: list[list[float]] = []
    espera_reintento = ESPERA_REINTENTO_INICIAL

    def recorrer(
        puntos: list[list[float]],
        *,
        bucle: bool = False,
        vigente: Callable[[], bool] | None = None,
    ) -> tuple[list[list[float]], bool]:
        """Emite un tramo punto por punto, con la espera del tramo siguiente.

        Antes de cada punto consulta `vigente`: si el viaje cambió, corta para
        que el llamador planifique de nuevo. Devuelve los puntos emitidos y si
        llegó al final del tramo.
        """
        nonlocal ultimo, ultimo_rumbo
        emitidos: list[list[float]] = []
        total = len(puntos)
        for i, (lat, lon) in enumerate(puntos):
            if stop_event.is_set():
                return emitidos, False
            if i > 0 and vigente is not None and not vigente():
                print(f"--- 🔀 Camión #{truck_id}: su viaje cambió, recalcula la ruta ---")
                return emitidos, False
            referencia = puntos[i - 1] if i > 0 else ultimo
            dist = 0.0
            if referencia is not None:
                dist = calcular_distancia_metros(
                    referencia[0], referencia[1], lat, lon
                )
            if referencia is not None and dist >= 1:
                rumbo = calcular_rumbo(referencia[0], referencia[1], lat, lon)
                cardinal = punto_cardinal(rumbo)
                _, velocidad_kmh = espera_y_velocidad(
                    dist, intervalo, objetivo_kmh
                )
                telemetria_str = (
                    f"| Rumbo: {rumbo:5.1f}° {cardinal:2}"
                    f" | Vel: {velocidad_kmh:4.1f} km/h | Tramo: {dist:4.1f}m"
                )
            else:
                # Parado: conserva el rumbo para que el ícono no gire al norte.
                rumbo = ultimo_rumbo
                velocidad_kmh = 0
                telemetria_str = "| Punto de partida"

            # La espera es la del tramo que viene: el camión tarda en llegar al
            # próximo punto, no en llegar al que acaba de reportar.
            espera = espera_hacia_el_siguiente(
                puntos, i, intervalo, objetivo_kmh, bucle=bucle
            )

            # Hora de medición: el instante en que el simulador toma la lectura, no el envío.
            medido_en = datetime.now(UTC)
            ok = sender(lat, lon, velocidad_kmh, rumbo, medido_en)
            status = "🟢 OK" if ok else "🔴 FAIL"

            print(
                f"[{i + 1:3}/{total}] {status} | Lat: {lat:10.6f}, Long: {lon:10.6f} "
                f"{telemetria_str}"
            )
            ultimo = [lat, lon]
            ultimo_rumbo = rumbo
            emitidos.append(ultimo)
            stop_event.wait(espera)
        return emitidos, True

    def esperar_en_el_lugar(motivo: str) -> None:
        """Se queda donde está, reportando su posición, hasta el próximo intento."""
        nonlocal espera_reintento
        print(f"⏸️ Camión #{truck_id}: {motivo}. Reintenta en {espera_reintento:.0f}s.")
        if ultimo is not None:
            sender(ultimo[0], ultimo[1], 0.0, ultimo_rumbo, datetime.now(UTC))
        stop_event.wait(espera_reintento)
        espera_reintento = min(espera_reintento * 2, ESPERA_REINTENTO_MAXIMA)

    def consultar() -> Objetivo | None:
        viajes = listar_viajes(truck_id, admin_headers)
        return None if viajes is None else objetivo_del_camion(viajes)

    def mientras(
        regla: Callable[[Objetivo, Objetivo], bool], inicial: Objetivo
    ) -> Callable[[], bool]:
        """Chequeo previo a cada punto: el plan sigue valiendo para el viaje actual."""

        def vigente() -> bool:
            actual = consultar()
            # Si la API no contesta no se corta: un corte no cambia el viaje.
            return actual is None or regla(inicial, actual)

        return vigente

    def circuito_desde_aca() -> list[list[float]]:
        """La vuelta arranca en el punto del circuito más cercano al camión.

        Empezar siempre en el punto 0 lo hacía saltar kilómetros. Si el camión
        quedó lejos del circuito, se une con una recta.
        """
        if ultimo is None:
            return circuito
        k = indice_mas_cercano(circuito, ultimo)
        vuelta = circuito[k:] + circuito[:k]
        return interpolar(ultimo, vuelta[0])[1:-1] + vuelta

    def tramo_hacia(viaje_id: int, destino: dict) -> list[list[float]] | None:
        """Camino hasta `destino`, el mismo que dibuja el mapa; `None` si no hay."""
        ruta = pedir_ruta(viaje_id, admin_headers)
        if ruta.estado == 200 and len(ruta.puntos) > 1:
            print(
                f"\n--- 🧭 Camión #{truck_id}: ruta por calles hasta la parada "
                f"{destino.get('seq')} ({len(ruta.puntos)} puntos) ---"
            )
            return ruta.puntos
        if ruta.estado == 503:
            # Sin proveedor de ruteo el mapa dibuja una recta punteada hasta la
            # parada: el camión va por esa misma recta.
            print(
                f"\n--- 📏 Camión #{truck_id}: sin proveedor de ruteo, recta hasta "
                f"la parada {destino.get('seq')} ---"
            )
            return interpolar(ultimo or circuito[0], [destino["lat"], destino["lng"]])
        if ruta.estado == 409 and ultimo is None:
            # Sin telemetría ni depósito la ruta no tiene origen: el camión
            # aparece al principio de su circuito y desde ahí se planifica.
            recorrer(circuito[:1])
            return None
        esperar_en_el_lugar(
            f"no hay ruta hasta la parada {destino.get('seq')} "
            f"(respuesta {ruta.estado or 'ninguna'})"
        )
        return None

    def salir_de_la_parada(objetivo: Objetivo) -> None:
        """Deja el radio de la parada alcanzada para que el viaje la entregue.

        Pasa en la última: no queda destino y, si el camión se quedara quieto,
        el viaje no se cerraría nunca. Antes daba una vuelta entera al circuito
        fijo, empezando a kilómetros. Ahora vuelve por donde vino hasta que la
        parada figura entregada.
        """
        parada = objetivo.proxima or {}
        print(
            f"\n--- ↩️ Camión #{truck_id}: en la parada {parada.get('seq')} y sin otra "
            "a la que ir; sale de su radio para entregarla ---"
        )
        if len(ultimo_tramo) > 1:
            _, completo = recorrer(
                list(reversed(ultimo_tramo)),
                vigente=mientras(sigue_en_la_parada, objetivo),
            )
            if not completo:
                return
        # Sin un tramo por donde volver (o con uno más corto que el radio), el
        # viaje se reabre directamente para no quedar en la parada para siempre.
        # Si ya se cerró, `reiniciar_viaje` no encuentra nada abierto y no toca
        # nada. La pausa evita golpear la API sin descanso si el reinicio falla.
        reiniciar_viaje(truck_id, headers=admin_headers)
        stop_event.wait(max(intervalo, 1.0))

    vuelta = 1
    while not stop_event.is_set():
        if not admin_headers:
            # Sin credenciales de admin no hay viajes que consultar: el camión
            # recorre su circuito.
            print(f"\n--- 🔄 Iniciando Vuelta #{vuelta} del circuito ---")
            recorrer(circuito_desde_aca(), bucle=True)
            vuelta += 1
            continue

        objetivo = consultar()
        if objetivo is None:
            esperar_en_el_lugar("no se pudieron leer sus viajes")
            continue

        if objetivo.viaje_id is None:
            # Los viajes se cierran solos al entregar la última parada: se
            # reabre el último y en la próxima pasada ya tiene ruta.
            if renovar_viaje(truck_id, admin_headers):
                continue
            print(f"\n--- 🔄 Camión #{truck_id} sin viaje: vuelta #{vuelta} del circuito ---")
            recorrer(
                circuito_desde_aca(),
                bucle=True,
                vigente=mientras(sin_viaje_abierto, objetivo),
            )
            vuelta += 1
            continue

        if objetivo.destino is not None:
            tramo = tramo_hacia(objetivo.viaje_id, objetivo.destino)
            if tramo is None:
                continue
            if longitud_m(tramo) >= RUTA_MINIMA_M:
                emitidos, _ = recorrer(tramo, vigente=mientras(sigue_el_tramo, objetivo))
                if len(emitidos) > 1:
                    ultimo_tramo = emitidos
                espera_reintento = ESPERA_REINTENTO_INICIAL
                continue

        proxima = objetivo.proxima
        if proxima is not None and proxima.get("status") == "arrived":
            salir_de_la_parada(objetivo)
            espera_reintento = ESPERA_REINTENTO_INICIAL
            continue

        esperar_en_el_lugar(
            "su viaje no tiene una parada a la que ir (sin coordenada, o ya está "
            "en ella y el viaje no la marca)"
        )


def ejecutar_simulaciones(
    base_id: int,
    base_plate: str,
    intervalo: float,
    count: int,
    keep_history: bool = False,
    force: bool = False,
    objetivo_kmh: float = 55.0,
    plates: Sequence[str] | None = None,
):
    """Run all configured truck workers until interrupted.

    Telemetry only enters through `POST /devices/ingest`: each truck gets a
    simulated device and writes with its token, the same path a real ESP32
    uses. Trucks held by a real device are skipped unless `force` is set.

    Cada corrida arranca con el recorrido vacío (`keep_history=True` lo
    conserva). Sólo se borra el historial de los camiones que llegaron hasta
    acá: los que tienen hardware real se saltean antes, así que su recorrido
    nunca se toca.
    """
    admin_headers = dict(autenticar_admin())
    if not admin_headers:
        print("⛔ El simulador necesita ADMIN_API_USER/ADMIN_API_PASSWORD. Abortando.")
        return False

    trabajos = []
    flota = build_truck_configs(base_id, base_plate, count, plates=plates)
    for config in flota:
        registrar_camion(config.truck_id, config.plate, headers=admin_headers)
        token = preparar_dispositivo(config.truck_id, admin_headers, force=force)
        if token is None:
            continue
        if not keep_history:
            limpiar_recorrido(config.truck_id, headers=admin_headers)
            reiniciar_viaje(config.truck_id, headers=admin_headers)
        trabajos.append(
            (
                config,
                constructor_de_sender(
                    token,
                    # `partial` fija el truck_id: un cierre sobre el bucle
                    # capturaría el último config y los tres camiones
                    # compartirían el mismo dispositivo. La recuperación
                    # renueva el JWT de admin antes de re-aprovisionar.
                    on_unauthorized=partial(
                        _reaprovisionar_dispositivo, config.truck_id, admin_headers
                    ),
                ),
            )
        )
    if not trabajos:
        print("⛔ Ningún camión quedó disponible para simular. Abortando.")
        return False

    stop_event = Event()
    executor = ThreadPoolExecutor(max_workers=max(len(trabajos), 1))
    futures = [
        executor.submit(
            simular_ruta,
            config.truck_id,
            config.plate,
            intervalo,
            stop_event,
            config.route_offset,
            route_file=config.route_file,
            admin_headers=admin_headers,
            sender=sender,
            objetivo_kmh=objetivo_kmh,
        )
        for config, sender in trabajos
    ]
    try:
        for future in futures:
            future.result()
    except KeyboardInterrupt:
        print("\n⏹️ Deteniendo simulaciones...")
        stop_event.set()
    finally:
        stop_event.set()
        executor.shutdown(wait=True, cancel_futures=True)
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de camión con ruta urbana realista en Córdoba")
    parser.add_argument("--id", type=int, default=1, help="ID del camión (default: 1)")
    parser.add_argument(
        "--plate",
        type=str,
        default=None,
        help=(
            "Patente base. Sin esta opción, con varios camiones se usa la lista "
            "TRUCK_PLATES (por defecto ABC123, DEF456, XYZ789)."
        ),
    )
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Intervalo en segundos entre pings (default: 2.0)")
    parser.add_argument("-n", "--count", type=int, default=1, help="Cantidad de camiones (default: 1)")
    parser.add_argument(
        "--speed-kmh",
        type=float,
        default=55.0,
        help=(
            "Velocidad objetivo en km/h. Los tramos largos esperan lo necesario para "
            "no superarla; --interval queda como cadencia mínima (default: 55)."
        ),
    )
    parser.add_argument(
        "--keep-history",
        action="store_true",
        help=(
            "Conserva el recorrido anterior de cada camión. Por defecto se borra "
            "al arrancar: los puntos de una corrida previa quedan a kilómetros de "
            "la nueva y el mapa dibuja un recorrido que el camión no hizo."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Revoca el dispositivo que ocupa el camión para poder simularlo. "
            "Vas a tener que volver a aprovisionar ese ESP32."
        ),
    )

    args = parser.parse_args()
    ok = ejecutar_simulaciones(
        base_id=args.id,
        base_plate=args.plate or DEFAULT_BASE_PLATE,
        # Una patente pedida a mano manda para un solo camión; con varios, la
        # lista compartida es la que mantiene seed y simulador de acuerdo.
        plates=truck_plates() if args.plate is None else None,
        intervalo=args.interval,
        count=args.count,
        keep_history=args.keep_history,
        force=args.force,
        objetivo_kmh=args.speed_kmh,
    )
    raise SystemExit(0 if ok else 1)
