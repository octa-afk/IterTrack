"""Límite de intentos en memoria, con ventana deslizante.

Alcanza con un solo proceso de uvicorn, que es como se despliega hoy. Con varios
workers o réplicas cada uno contaría por separado y habría que mover esto a un
almacén compartido.
"""

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

# Más que la ventana más larga en uso: lo más viejo ya no decide nada.
MAX_WINDOW_SECONDS = 3600
PURGE_EVERY_SECONDS = 300


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()
        self._last_purge = clock()

    def retry_after(self, key: str, limit: int, window: int) -> int:
        """Segundos hasta poder reintentar; 0 si la clave no está bloqueada."""
        now = self._clock()
        with self._lock:
            recent = [hit for hit in self._hits.get(key, ()) if now - hit < window]
            if len(recent) < limit:
                return 0
            # El cupo se libera cuando vence el golpe que completó el límite.
            return max(1, math.ceil(recent[-limit] + window - now))

    def record(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._purge(now)
            self._hits.setdefault(key, deque()).append(now)

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _purge(self, now: float) -> None:
        """Descarta lo vencido: las claves las elige el cliente y no deben acumularse."""
        if now - self._last_purge < PURGE_EVERY_SECONDS:
            return
        self._last_purge = now
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and now - hits[0] >= MAX_WINDOW_SECONDS:
                hits.popleft()
            if not hits:
                del self._hits[key]


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    """IP del cliente. Detrás de Caddy depende de `--proxy-headers` en uvicorn."""
    return request.client.host if request.client else "unknown"
