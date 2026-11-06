"""Genera los circuitos de demo que recorre cada camión simulado.

Los trazados se piden a OSRM (datos de OpenStreetMap) una sola vez y se guardan
en el repo: el simulador y el seed nunca salen a la red. Este script es una
herramienta de mantenimiento, no parte del arranque.

Cada circuito es un lazo cerrado: el último punto es el primero, porque el
simulador vuelve al índice 0 al terminar una vuelta.

Usage:
    env/bin/python -m scripts.generate_demo_routes
"""

import json
import math
from itertools import pairwise
from pathlib import Path

import requests

ROUTES_DIR = Path(__file__).resolve().parent
OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
# Atribución obligatoria: los trazados derivan de OpenStreetMap (ODbL).
USER_AGENT = "IterTrack-demo-routes/1.0 (+https://github.com/octa-afk/IterTrack)"
# Separación objetivo entre puntos: ~25 m. Más denso no aporta (el simulador
# espera según la distancia al punto siguiente) y agranda el archivo.
SPACING_M = 25.0
METERS_PER_DEGREE = 111_320.0

# Waypoints (lat, lng) aproximados sobre avenidas reales; OSRM los ajusta a la
# calle más cercana. El primero se repite al final para cerrar el lazo.
CIRCUITS: dict[str, list[tuple[float, float]]] = {
    "cordoba_route_norte.json": [
        (-31.3836, -64.2300),  # Cerro de las Rosas
        (-31.3720, -64.2400),  # Villa Belgrano
        (-31.3640, -64.2620),  # Argüello
        (-31.3900, -64.2100),  # Villa Cabrera
        (-31.3836, -64.2300),  # cierre
    ],
    "cordoba_route_sur.json": [
        (-31.4420, -64.1830),  # Vélez Sarsfield y Fuerza Aérea
        (-31.4470, -64.1672),  # Barrio Jardín
        (-31.4303, -64.1520),  # Av. Cruz Roja
        (-31.4180, -64.1646),  # Garzón Agulla
        (-31.4420, -64.1830),  # cierre
    ],
    "cordoba_route_norte_sur.json": [
        (-31.3640, -64.2620),  # Argüello
        (-31.3836, -64.2300),  # Cerro de las Rosas
        (-31.4201, -64.1888),  # Plaza San Martín
        (-31.4470, -64.1672),  # Barrio Jardín
        (-31.4303, -64.1520),  # Av. Cruz Roja
        (-31.3900, -64.2100),  # Villa Cabrera
        (-31.3640, -64.2620),  # cierre
    ],
}


def distance_m(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Distancia aproximada entre dos puntos (lat, lng), suficiente a esta escala."""
    dlat = (second[0] - first[0]) * METERS_PER_DEGREE
    dlng = (second[1] - first[1]) * METERS_PER_DEGREE * math.cos(math.radians(first[0]))
    return math.hypot(dlat, dlng)


def fetch_loop(waypoints: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Pide el lazo a OSRM y devuelve los puntos como (lat, lng)."""
    coords = ";".join(f"{lng},{lat}" for lat, lng in waypoints)
    url = f"{OSRM_URL}/{coords}?overview=full&geometries=geojson&continue_straight=false"
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RuntimeError(f"OSRM no devolvió una ruta: {payload.get('code')}")
    return [(lat, lon) for lon, lat in payload["routes"][0]["geometry"]["coordinates"]]


def thin(points: list[tuple[float, float]], spacing: float = SPACING_M) -> list[tuple[float, float]]:
    """Deja un punto cada `spacing` metros y garantiza que el lazo cierre."""
    if not points:
        return []
    kept = [points[0]]
    for point in points[1:]:
        if distance_m(kept[-1], point) >= spacing:
            kept.append(point)
    kept.append(kept[0])
    return [(round(lat, 6), round(lng, 6)) for lat, lng in kept]


def main() -> int:
    for filename, waypoints in CIRCUITS.items():
        crude = fetch_loop(waypoints)
        points = thin(crude)
        length_km = sum(
            distance_m(first, second) for first, second in pairwise(points)
        ) / 1000
        target = ROUTES_DIR / filename
        target.write_text(json.dumps(points), encoding="utf-8")
        print(f"✅ {filename}: {len(points)} puntos, {length_km:.1f} km")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
