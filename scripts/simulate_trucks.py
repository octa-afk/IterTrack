import os
import sys
import json
import math
import time
import argparse
import requests
from pathlib import Path

BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000/trucks")
ROUTE_FILE = Path(__file__).parent / "cordoba_route.json"

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

def registrar_camion(truck_id: int, lat: float, long: float, plate: str):
    """Registra el camión si aún no existe en el sistema."""
    try:
        response = requests.post(
            BASE_URL,
            json={
                "truck": {"id": truck_id, "plate": plate},
                "location": {"lat": lat, "long": long}
            },
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

def limpiar_recorrido(truck_id: int):
    """Borra todo el recorrido registrado del camión llamando a DELETE /trucks/{id}/iter."""
    try:
        response = requests.delete(f"{BASE_URL}/{truck_id}/iter", timeout=5)
        if response.status_code == 204:
            print(f"🗑️ Recorrido del camión #{truck_id} borrado correctamente.")
        else:
            print(f"⚠️ No se pudo borrar el recorrido: {response.status_code}")
    except requests.RequestException as e:
        print(f"⚠️ Error al borrar recorrido: {e}")

def actualizar_ubicacion(truck_id: int, lat: float, long: float) -> bool:
    """Envía la nueva coordenada del camión al endpoint PUT /trucks/{id}/location."""
    try:
        response = requests.put(
            f"{BASE_URL}/{truck_id}/location",
            json={"lat": lat, "long": long},
            timeout=5
        )
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"⚠️ Error al actualizar ubicación: {e}")
        return False

def simular_ruta(truck_id: int, plate: str, intervalo: float):
    ruta = cargar_ruta()
    total_puntos = len(ruta)
    print(f"\n🚚 Iniciando simulación de ruta urbana en Córdoba ({total_puntos} puntos)")
    print(f"⏱️ Intervalo: {intervalo}s entre pings | API: {BASE_URL}\n")

    # Registrar el camión en su punto inicial
    lat_inicial, lon_inicial = ruta[0]
    registrar_camion(truck_id, lat_inicial, lon_inicial, plate)

    vuelta = 1
    while True:
        print(f"\n--- 🔄 Iniciando Vuelta #{vuelta} del circuito ---")
        limpiar_recorrido(truck_id)
        for i, (lat, lon) in enumerate(ruta):
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

            ok = actualizar_ubicacion(truck_id, lat, lon)
            status = "🟢 OK" if ok else "🔴 FAIL"

            print(f"[{i + 1:3}/{total_puntos}] {status} | Lat: {lat:10.6f}, Long: {lon:10.6f} {telemetria_str}")
            time.sleep(intervalo)

        vuelta += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de camión con ruta urbana realista en Córdoba")
    parser.add_argument("--id", type=int, default=1, help="ID del camión (default: 1)")
    parser.add_argument("--plate", type=str, default="ABC123", help="Patente del camión (default: ABC123)")
    parser.add_argument("-i", "--interval", type=float, default=2.0, help="Intervalo en segundos entre pings (default: 2.0)")

    args = parser.parse_args()
    simular_ruta(truck_id=args.id, plate=args.plate, intervalo=args.interval)