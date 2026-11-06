"""Dirección -> coordenada, detrás de una interfaz.

El proveedor es intercambiable a propósito: en desarrollo no hay proveedor
(`none`) o se usa Nominatim; en el lanzamiento se evalúa Google. El dominio
—`TripStop`, `AddressCache`— no sabe cuál está detrás.

La política pública de Nominatim limita a 1 request por segundo, un solo hilo y
4 requests por minuto para scripts periódicos. Por eso el proveedor se
autolimita y, sobre todo, por eso la caché no es una optimización: es el
requisito que hace usable cualquier proveedor.
"""

import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from typing import Protocol

import httpx

from source.database.config import settings

NOMINATIM_MIN_INTERVAL_S = 1.0


@dataclass(frozen=True)
class GeoResult:
    lat: float
    lng: float
    provider: str
    confidence: float | None = None


class Geocoder(Protocol):
    name: str

    def geocode(self, address: str) -> GeoResult | None: ...


class NullGeocoder:
    """Sin proveedor configurado: todo destino queda pendiente de revisión."""

    name = "none"

    def geocode(self, address: str) -> GeoResult | None:
        return None


class NominatimGeocoder:
    """Cliente mínimo de Nominatim con autolimitación a 1 request/segundo."""

    name = "nominatim"

    def __init__(
        self,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float = 5.0,
        country_codes: str = "ar",
    ) -> None:
        self.base_url = (base_url or settings.geocoder_url).rstrip("/")
        self.user_agent = user_agent or settings.geocoder_user_agent
        self.timeout = timeout
        self.country_codes = country_codes
        self._lock = threading.Lock()
        self._last_call = 0.0

    def _throttle(self) -> None:
        with self._lock:
            wait = NOMINATIM_MIN_INTERVAL_S - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def geocode(self, address: str) -> GeoResult | None:
        self._throttle()
        try:
            response = httpx.get(
                f"{self.base_url}/search",
                params={
                    "q": address,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": self.country_codes,
                },
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
        except httpx.HTTPError:
            # Un proveedor caído no puede romper la importación: el destino
            # queda pendiente y se resuelve a mano.
            return None
        if response.status_code != 200:
            return None
        try:
            results = response.json()
        except ValueError:
            return None
        if not results:
            return None
        first = results[0]
        try:
            lat = float(first["lat"])
            lng = float(first["lon"])
        except (KeyError, TypeError, ValueError):
            return None
        importance = first.get("importance")
        return GeoResult(
            lat=lat,
            lng=lng,
            provider=self.name,
            confidence=float(importance) if importance is not None else None,
        )


def get_geocoder() -> Geocoder:
    """Dependencia de FastAPI: los tests la sobrescriben y nunca salen a la red."""
    provider = (settings.geocoder_provider or "none").strip().lower()
    if provider == "nominatim":
        return NominatimGeocoder()
    return NullGeocoder()


def normalize_address(address: str) -> str:
    """Clave de caché: sin acentos, minúsculas, espacios colapsados.

    "Av. Colón 1234" y "AV COLON 1234" tienen que pegarle a la misma fila; si no,
    la caché se llena de duplicados y cada importación vuelve a geocodificar.
    """
    text = unicodedata.normalize("NFD", address)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[.,;]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()
