import argparse
import json
import math
import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from threading import Event, Lock
from time import monotonic
from typing import Any, Protocol
from uuid import uuid4

import requests

SCRIPT_ENV_FILE = Path(__file__).resolve().parent / ".env"

# Cuánto esperar antes de reintentar una recuperación de token que ya falló.
# Sin esto, un camión tomado por hardware real golpearía los endpoints de
# administración en cada punto de telemetría.
RECOVERY_COOLDOWN = 30.0


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

ROUTE_FILE = Path(__file__).resolve().parent / "cordoba_route.json"

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


def build_truck_configs(
    base_id: int,
    base_plate: str,
    count: int,
    route_length: int | None = None,
) -> list[TruckConfig]:
    """Build deterministic identities and route offsets for the workers."""
    if count < 1:
        raise ValueError("count must be at least 1")

    offsets = (
        [route_offset(route_length, index, count) for index in range(count)]
        if route_length is not None
        else list(range(count))
    )
    return [
        TruckConfig(
            truck_id=base_id + index,
            plate=base_plate if count == 1 else f"{base_plate}-{index + 1:02d}",
            route_offset=offsets[index],
        )
        for index in range(count)
    ]


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


def autenticar() -> dict:
    """Login de telemetría con API_USER / API_PASSWORD."""
    return _login("API_USER", "API_PASSWORD", "telemetría")


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

def cargar_ruta():
    """Carga los puntos de la ruta realista desde el archivo JSON."""
    if ROUTE_FILE.exists():
        with open(ROUTE_FILE, encoding="utf-8") as f:
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
    lat: float,
    long: float,
    plate: str,
    speed: float = 0,
    heading: float = 0,
    headers=None,
):
    """Registra el camión si aún no existe en el sistema."""
    try:
        response = requests.post(
            BASE_URL,
            json={
                "truck": {"id": truck_id, "plate": plate},
                "location": {
                    "lat": lat,
                    "long": long,
                    "speed": speed,
                    "heading": heading,
                }
            },
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

def actualizar_ubicacion(
    truck_id: int,
    lat: float,
    long: float,
    speed: float,
    heading: float,
    recorded_at: datetime,
    headers=None,
    on_unauthorized=None,
) -> bool:
    """Envía la coordenada y su hora de medición al endpoint PUT /trucks/{id}/location.

    Si el token venció (401) y hay un callback ``on_unauthorized``, renueva las
    credenciales y reintenta una sola vez. Sin eso la simulación se queda
    reportando fallos para siempre y el mapa se congela.
    """
    payload: dict[str, Any] = {
        "lat": lat,
        "long": long,
        "speed": speed,
        "heading": heading,
        "recorded_at": recorded_at.isoformat(),
    }

    def enviar(auth_headers):
        return requests.put(
            f"{BASE_URL}/{truck_id}/location",
            json=payload,
            headers=HEADERS if auth_headers is None else auth_headers,
            timeout=5,
        )

    try:
        response = enviar(headers)
        if response.status_code == 401 and on_unauthorized is not None:
            response = enviar(on_unauthorized())
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"⚠️ Error al actualizar ubicación: {e}")
        return False

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
        estado["ultimo_intento"] = monotonic()
        nuevo = on_unauthorized() if on_unauthorized is not None else None
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
    headers=None,
    stop_event: StopSignal | None = None,
    phase_offset: int = 0,
    clear_history_on_start: bool = False,
    admin_headers=None,
    refresh_headers=None,
    sender=None,
):
    ruta = rotate_route(cargar_ruta(), phase_offset)
    total_puntos = len(ruta)
    print(f"\n🚚 Iniciando simulación de ruta urbana en Córdoba ({total_puntos} puntos)")
    print(f"⏱️ Intervalo: {intervalo}s entre pings | API: {BASE_URL}\n")

    if headers is None:
        headers = autenticar()
    if stop_event is None:
        stop_event = Event()

    # Un solo re-login actualiza el dict compartido, así todos los hilos de
    # simulación se recuperan juntos del vencimiento del token.
    on_unauthorized = None
    if refresh_headers is not None:

        def _renew() -> dict:
            renovado = dict(refresh_headers())
            if renovado:
                headers.clear()
                headers.update(renovado)
            return headers

        on_unauthorized = _renew

    # Modo usuario: la telemetría va por PUT /trucks/{id}/location con credenciales
    # de usuario. Modo dispositivo inyecta un sender que habla el protocolo del hardware.
    if sender is None:

        def _enviar_como_usuario(lat, lon, velocidad, rumbo, medido_en) -> bool:
            update_kwargs = {
                "speed": velocidad,
                "heading": rumbo,
                "recorded_at": medido_en,
                "headers": headers,
            }
            if on_unauthorized is not None:
                update_kwargs["on_unauthorized"] = on_unauthorized
            return actualizar_ubicacion(truck_id, lat, lon, **update_kwargs)

        sender = _enviar_como_usuario

    # El registro y la limpieza son operaciones de administración; la
    # telemetría la puede enviar cualquier usuario de la organización.
    registration_headers = admin_headers if admin_headers else headers

    # Registrar el camión en su punto inicial
    lat_inicial, lon_inicial = ruta[0]
    registrar_camion(truck_id, lat_inicial, lon_inicial, plate, headers=registration_headers)
    if clear_history_on_start:
        limpiar_recorrido(truck_id, headers=registration_headers)

    vuelta = 1
    while not stop_event.is_set():
        print(f"\n--- 🔄 Iniciando Vuelta #{vuelta} del circuito ---")
        for i, (lat, lon) in enumerate(ruta):
            if stop_event.is_set():
                break
            # Calcular rumbo respecto al punto anterior
            if i > 0:
                prev_lat, prev_lon = ruta[i - 1]
                dist = calcular_distancia_metros(prev_lat, prev_lon, lat, lon)
                rumbo = calcular_rumbo(prev_lat, prev_lon, lat, lon)
                cardinal = punto_cardinal(rumbo)
                velocidad_kmh = (dist / intervalo) * 3.6
                telemetria_str = f"| Rumbo: {rumbo:5.1f}° {cardinal:2} | Vel: {velocidad_kmh:4.1f} km/h | Tramo: {dist:4.1f}m"
            else:
                rumbo = 0
                velocidad_kmh = 0
                telemetria_str = "| Punto de partida"

            # Hora de medición: el instante en que el simulador toma la lectura, no el envío.
            medido_en = datetime.now(UTC)
            ok = sender(lat, lon, velocidad_kmh, rumbo, medido_en)
            status = "🟢 OK" if ok else "🔴 FAIL"

            print(f"[{i + 1:3}/{total_puntos}] {status} | Lat: {lat:10.6f}, Long: {lon:10.6f} {telemetria_str}")
            stop_event.wait(intervalo)

        vuelta += 1


def ejecutar_simulaciones(
    base_id: int,
    base_plate: str,
    intervalo: float,
    count: int,
    clear_history_on_start: bool = False,
    mode: str = "user",
    force: bool = False,
):
    """Run all configured truck workers until interrupted.

    `mode="user"` writes through PUT /trucks/{id}/location.
    `mode="device"` provisions a simulated device per truck and writes through
    POST /devices/ingest, the same path a real ESP32 uses, so the hardware
    pipeline is exercised. Trucks already held by a real device are skipped
    unless `force` is set.
    """
    if mode not in ("user", "device"):
        raise ValueError("mode must be 'user' or 'device'")

    route_length = len(cargar_ruta())
    configs = build_truck_configs(base_id, base_plate, count, route_length)
    admin_headers = dict(autenticar_admin())
    if not admin_headers:
        print("ℹ️ Sin ADMIN_API_USER/ADMIN_API_PASSWORD: el registro usará la cuenta de telemetría.")  # noqa: RUF001

    if mode == "device":
        if not admin_headers:
            print("⛔ El modo dispositivo necesita ADMIN_API_USER/ADMIN_API_PASSWORD. Abortando.")
            return False
        trabajos = []
        ruta = cargar_ruta()
        lat_inicial, lon_inicial = ruta[0]
        for config in configs:
            registrar_camion(
                config.truck_id, lat_inicial, lon_inicial, config.plate, headers=admin_headers
            )
            token = preparar_dispositivo(config.truck_id, admin_headers, force=force)
            if token is None:
                continue
            trabajos.append(
                (
                    config,
                    constructor_de_sender(
                        token,
                        # `partial` fija el truck_id: un cierre sobre el bucle
                        # capturaría el último config y los tres camiones
                        # compartirían el mismo dispositivo.
                        on_unauthorized=partial(
                            preparar_dispositivo, config.truck_id, admin_headers
                        ),
                    ),
                )
            )
        if not trabajos:
            print("⛔ Ningún camión quedó disponible para simular. Abortando.")
            return False
    else:
        headers = dict(autenticar())
        if not headers:
            print("⛔ Sin token no se puede enviar telemetría. Abortando.")
            return False
        admin_headers = admin_headers or headers
        trabajos = [(config, None) for config in configs]

    refresh_lock = Lock()

    def renovar_credenciales() -> dict:
        """Re-login serializado: un token nuevo sirve a todos los camiones."""
        with refresh_lock:
            return dict(autenticar())

    stop_event = Event()
    executor = ThreadPoolExecutor(max_workers=max(len(trabajos), 1))
    futures = [
        executor.submit(
            simular_ruta,
            config.truck_id,
            config.plate,
            intervalo,
            {} if sender is not None else headers,
            stop_event,
            config.route_offset,
            clear_history_on_start=clear_history_on_start,
            admin_headers=admin_headers,
            refresh_headers=None if sender is not None else renovar_credenciales,
            sender=sender,
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
    parser.add_argument("--plate", type=str, default="ABC123", help="Patente del camión (default: ABC123)")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Intervalo en segundos entre pings (default: 2.0)")
    parser.add_argument("-n", "--count", type=int, default=1, help="Cantidad de camiones (default: 1)")
    parser.add_argument(
        "--clear-history-on-start",
        action="store_true",
        help="Borra el historial existente de cada camión una sola vez al iniciar (opción destructiva)",
    )
    parser.add_argument(
        "--mode",
        choices=("user", "device"),
        default="user",
        help=(
            "user: escribe por PUT /trucks/{id}/location. "
            "device: aprovisiona un dispositivo simulado y escribe por "
            "POST /devices/ingest, igual que un ESP32."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "En modo device, revoca el dispositivo que ocupa el camión para poder "
            "simularlo. Vas a tener que volver a aprovisionar ese ESP32."
        ),
    )

    args = parser.parse_args()
    ok = ejecutar_simulaciones(
        base_id=args.id,
        base_plate=args.plate,
        intervalo=args.interval,
        count=args.count,
        clear_history_on_start=args.clear_history_on_start,
        mode=args.mode,
        force=args.force,
    )
    raise SystemExit(0 if ok else 1)
