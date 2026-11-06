"""Ruta por calles entre puntos, detrás de una interfaz.

Mismo patrón que el geocoder: el proveedor es intercambiable y el dominio
—viajes, paradas— no sabe cuál está detrás. En desarrollo no hay proveedor
(`none`) y el mapa cae a la línea recta; con `osrm` se pide la ruta real.

El servidor público de OSRM se usa para la demo, no para producción con carga:
no tiene SLA ni límite publicado y un pico de consultas lo degrada. El día que
haga falta, `OSRM_URL` apunta a una instancia propia sin tocar este módulo.
"""

from dataclasses import dataclass
from typing import Protocol

import httpx

from source.database.config import settings


@dataclass(frozen=True)
class RouteResult:
    """Geometría completa de la ruta, en (lat, lng)."""

    points: list[tuple[float, float]]
    distance_m: float
    duration_s: float
    provider: str


class Router(Protocol):
    name: str

    def route(self, points: list[tuple[float, float]]) -> RouteResult | None: ...


class NullRouter:
    """Sin proveedor configurado: el llamador decide qué mostrar en su lugar."""

    name = "none"

    def route(self, points: list[tuple[float, float]]) -> RouteResult | None:
        return None


class OsrmRouter:
    """Cliente mínimo del endpoint `/route` de OSRM."""

    name = "osrm"

    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or settings.routing_url).rstrip("/")
        self.timeout = timeout

    def route(self, points: list[tuple[float, float]]) -> RouteResult | None:
        if len(points) < 2:
            return None
        # OSRM espera `lon,lat`, separados por `;`. Invertirlos manda la ruta al
        # hemisferio equivocado.
        coordinates = ";".join(f"{lng},{lat}" for lat, lng in points)
        try:
            response = httpx.get(
                f"{self.base_url}/route/v1/driving/{coordinates}",
                params={
                    "overview": "full",
                    "geometries": "geojson",
                    "alternatives": "false",
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError:
            # Un proveedor caído no puede romper el mapa: el frontend vuelve a la
            # línea recta y el operador sigue viendo los destinos.
            return None
        if response.status_code != 200:
            return None
        try:
            body = response.json()
            route = body["routes"][0]
            coordinates = route["geometry"]["coordinates"]
            distance = float(route["distance"])
            duration = float(route["duration"])
            parsed = [(float(lat), float(lng)) for lng, lat in coordinates]
        except (KeyError, IndexError, TypeError, ValueError):
            # `code: NoRoute` y una respuesta con otra forma se tratan igual: sin
            # geometría no hay ruta que dibujar.
            return None
        if len(parsed) < 2:
            return None
        return RouteResult(
            points=parsed,
            distance_m=distance,
            duration_s=duration,
            provider=self.name,
        )


def get_router() -> Router:
    """Dependencia de FastAPI: los tests la sobrescriben y nunca salen a la red."""
    provider = (settings.routing_provider or "none").strip().lower()
    if provider == "osrm":
        return OsrmRouter()
    return NullRouter()
