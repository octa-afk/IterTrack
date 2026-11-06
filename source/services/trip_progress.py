"""Progreso automático de un viaje a partir de la telemetría.

Un viaje no se mueve solo: lo mueve el camión. Cada punto aceptado por
`POST /devices/ingest` mira si el camión entró al depósito o a una parada, y
recién cuando sale del radio de la parada la da por entregada.

Sin esto el estado se queda en `planned` para siempre: el operador ve el camión
moverse y la sección Rutas congelada.
"""

from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from source.models.destination import Depot, Trip, TripStop

OPEN_TRIP_STATUSES = ("planned", "in_progress")
# Un destino es una dirección, no un punto: 120 m cubre la vereda de enfrente, el
# error del GPS y que el camión estacione en la esquina.
STOP_RADIUS_M = 120

_EARTH_RADIUS_M = 6_371_000.0


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos coordenadas (haversine)."""
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    h = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_M * asin(sqrt(h))


def _open_trip(db: Session, truck_id: int) -> Trip | None:
    """El viaje abierto del camión; si hubiera más de uno, el más reciente."""
    return (
        db.query(Trip)
        .filter(Trip.truck_id == truck_id, Trip.status.in_(OPEN_TRIP_STATUSES))
        .order_by(Trip.departure_at.desc())
        .first()
    )


def _start_at_depot(db: Session, trip: Trip, lat: float, lng: float) -> None:
    if trip.status != "planned" or trip.depot_id is None:
        return
    depot = db.get(Depot, trip.depot_id)
    if depot is None:
        return
    if distance_m(lat, lng, depot.lat, depot.lng) <= depot.radius_m:
        trip.status = "in_progress"


def _next_pending_stop(trip: Trip) -> TripStop | None:
    """La parada que toca: la primera por orden que no está entregada.

    El viaje es secuencial. Si el camión pasa cerca de la parada 3 antes de
    llegar a la 1, no se marca nada: darla por hecha desordenaría el recorrido
    que el dador de carga pactó.
    """
    for stop in trip.stops:
        if stop.status in ("pending", "arrived"):
            return stop
    return None


def _advance_stops(trip: Trip, lat: float, lng: float, measured_at: datetime) -> None:
    """Marca llegada al entrar al radio y entrega al salir.

    Sólo se evalúa la próxima parada del orden. Un destino sin coordenada no se
    puede confirmar: se saltea y deja el viaje abierto, porque darlo por
    entregado sería inventar la entrega.
    """
    stop = _next_pending_stop(trip)
    if stop is None or stop.lat is None or stop.lng is None:
        return
    distance = distance_m(lat, lng, stop.lat, stop.lng)
    if stop.status == "pending" and distance <= STOP_RADIUS_M:
        stop.status = "arrived"
        stop.arrived_at = measured_at
        # Si no hay depósito —o el camión no pasó por él— llegar a la primera
        # parada también significa que el viaje arrancó.
        if trip.status == "planned":
            trip.status = "in_progress"
    elif stop.status == "arrived" and distance > STOP_RADIUS_M:
        stop.status = "delivered"
        stop.departed_at = measured_at


def _finish_if_complete(trip: Trip) -> None:
    if trip.status != "in_progress" or not trip.stops:
        return
    if all(stop.status == "delivered" for stop in trip.stops):
        trip.status = "done"


def advance_trip_progress(
    db: Session,
    *,
    truck_id: int,
    lat: float,
    lng: float,
    measured_at: datetime,
) -> Trip | None:
    """Avanza el viaje abierto del camión con un punto de telemetría.

    Devuelve el viaje tocado, o `None` si el camión no tiene ninguno abierto.
    El llamador es dueño de la transacción: acá no se hace commit.
    """
    trip = _open_trip(db, truck_id)
    if trip is None:
        return None
    _start_at_depot(db, trip, lat, lng)
    _advance_stops(trip, lat, lng, measured_at)
    _finish_if_complete(trip)
    return trip
