import os
import sys
import json
import math
import time
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Event
import requests
from pathlib import Path

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/trucks")
AUTH_URL = os.getenv("AUTH_URL", "http://127.0.0.1:8000/auth/login")
ROUTE_FILE = Path(__file__).parent / "cordoba_route.json"

HEADERS = {}


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

def autenticar() -> dict:
    """Hace login y devuelve los headers con el Bearer token JWT."""
    username = os.getenv("API_USER", "octa")
    password = os.getenv("API_PASSWORD", "secreto123")
    try:
        response = requests.post(
            AUTH_URL,
            data={"username": username, "password": password},
            timeout=5,
        )
        if response.status_code == 200:
            token = response.json()["access_token"]
            print(f"🔑 Login OK como '{username}'.")
            return {"Authorization": f"Bearer {token}"}
        print(f"⚠️ Login falló ({response.status_code}): {response.text}")
    except requests.RequestException as e:
        print(f"⚠️ Error de conexión en login: {e}")
    return {}

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
        with open(ROUTE_FILE, "r", encoding="utf-8") as f:
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

def registrar_camion(truck_id: int, lat: float, long: float, plate: str, headers=None):
    """Registra el camión si aún no existe en el sistema."""
    try:
        response = requests.post(
            BASE_URL,
            json={
                "truck": {"id": truck_id, "plate": plate},
                "location": {"lat": lat, "long": long}
            },
            headers=HEADERS if headers is None else headers,
            timeout=5
        )
        if response.status_code in (200, 201):
            print(f"✅ Camión #{truck_id} ({plate}) registrado con éxito.")
        else:
            # Si ya existía, la API devuelve error o 200 con mensaje
            data = response.json() if response.headers.get("content-type") == "application/json" else response.text
            print(f"ℹ️ Info registro camión #{truck_id}: {data}")
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

def actualizar_ubicacion(truck_id: int, lat: float, long: float, headers=None) -> bool:
    """Envía la nueva coordenada del camión al endpoint PUT /trucks/{id}/location."""
    try:
        response = requests.put(
            f"{BASE_URL}/{truck_id}/location",
            json={"lat": lat, "long": long},
            headers=HEADERS if headers is None else headers,
            timeout=5
        )
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"⚠️ Error al actualizar ubicación: {e}")
        return False

def simular_ruta(
    truck_id: int,
    plate: str,
    intervalo: float,
    headers=None,
    stop_event: Event | None = None,
    phase_offset: int = 0,
):
    ruta = rotate_route(cargar_ruta(), phase_offset)
    total_puntos = len(ruta)
    print(f"\n🚚 Iniciando simulación de ruta urbana en Córdoba ({total_puntos} puntos)")
    print(f"⏱️ Intervalo: {intervalo}s entre pings | API: {BASE_URL}\n")

    if headers is None:
        headers = autenticar()
    if stop_event is None:
        stop_event = Event()

    # Registrar el camión en su punto inicial
    lat_inicial, lon_inicial = ruta[0]
    registrar_camion(truck_id, lat_inicial, lon_inicial, plate, headers=headers)

    vuelta = 1
    while not stop_event.is_set():
        print(f"\n--- 🔄 Iniciando Vuelta #{vuelta} del circuito ---")
        limpiar_recorrido(truck_id, headers=headers)
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
                telemetria_str = "| Punto de partida"

            ok = actualizar_ubicacion(truck_id, lat, lon, headers=headers)
            status = "🟢 OK" if ok else "🔴 FAIL"

            print(f"[{i + 1:3}/{total_puntos}] {status} | Lat: {lat:10.6f}, Long: {lon:10.6f} {telemetria_str}")
            stop_event.wait(intervalo)

        vuelta += 1


def ejecutar_simulaciones(base_id: int, base_plate: str, intervalo: float, count: int):
    """Authenticate once and run all configured truck workers until interrupted."""
    route_length = len(cargar_ruta())
    configs = build_truck_configs(base_id, base_plate, count, route_length)
    headers = dict(autenticar())
    stop_event = Event()
    executor = ThreadPoolExecutor(max_workers=count)
    futures = [
        executor.submit(
            simular_ruta,
            config.truck_id,
            config.plate,
            intervalo,
            headers,
            stop_event,
            config.route_offset,
        )
        for config in configs
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de camión con ruta urbana realista en Córdoba")
    parser.add_argument("--id", type=int, default=1, help="ID del camión (default: 1)")
    parser.add_argument("--plate", type=str, default="ABC123", help="Patente del camión (default: ABC123)")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Intervalo en segundos entre pings (default: 2.0)")
    parser.add_argument("-n", "--count", type=int, default=1, help="Cantidad de camiones (default: 1)")

    args = parser.parse_args()
    ejecutar_simulaciones(
        base_id=args.id,
        base_plate=args.plate,
        intervalo=args.interval,
        count=args.count,
    )
