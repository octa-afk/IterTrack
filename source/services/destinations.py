"""Dadores de carga, viajes y destinos.

La resolución dirección -> coordenada ocurre **sólo al importar**: se busca en
`address_cache`, y si no está se consulta al geocoder una vez. Un destino que no
se puede ubicar queda `needs_review=true` y se resuelve con un pin manual, que a
su vez escribe la caché para no volver a preguntar.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db
from source.services.auth import get_current_user, require_org_admin
from source.services.geocoding import Geocoder, get_geocoder, normalize_address
from source.services.routing import Router, get_router
from source.services.tracking import MEASUREMENT_ORDER

router = APIRouter(prefix="/chargers", tags=["chargers"])
depots_router = APIRouter(prefix="/depots", tags=["depots"])
trips_router = APIRouter(prefix="/trips", tags=["trips"])
destinations_router = APIRouter(prefix="/destinations", tags=["destinations"])

PROVIDED = "provided"
MANUAL = "manual"


def _get_cached(
    db: Session, organization_id: int, address: str
) -> models.AddressCache | None:
    return (
        db.query(models.AddressCache)
        .filter(
            models.AddressCache.organization_id == organization_id,
            models.AddressCache.address_norm == normalize_address(address),
        )
        .first()
    )


def _store_cache(
    db: Session,
    organization_id: int,
    address: str,
    lat: float,
    lng: float,
    provider: str,
    confidence: float | None = None,
    user_id: int | None = None,
) -> models.AddressCache:
    entry = _get_cached(db, organization_id, address)
    if entry is None:
        entry = models.AddressCache(
            organization_id=organization_id,
            address_norm=normalize_address(address),
            address_raw=address,
        )
        db.add(entry)
    entry.lat = lat
    entry.lng = lng
    entry.provider = provider
    entry.confidence = confidence
    entry.resolved_by_user_id = user_id
    entry.updated_at = datetime.now(UTC)
    db.flush()
    return entry


def _resolve_coordinates(
    db: Session,
    organization_id: int,
    stop: schemas.StopCreate,
    geocoder: Geocoder,
) -> tuple[float | None, float | None, str | None, float | None, bool]:
    """Devuelve (lat, lng, geo_source, confidence, needs_review)."""
    if stop.lat is not None and stop.lng is not None:
        _store_cache(
            db, organization_id, stop.address, stop.lat, stop.lng, PROVIDED
        )
        return stop.lat, stop.lng, PROVIDED, None, False

    cached = _get_cached(db, organization_id, stop.address)
    if cached is not None:
        return cached.lat, cached.lng, "cache", cached.confidence, False

    result = geocoder.geocode(stop.address)
    if result is None:
        # Sin coordenada no hay destino ubicable. No se inventa un centroide:
        # un pin equivocado manda al chofer al lugar incorrecto.
        return None, None, None, None, True

    _store_cache(
        db,
        organization_id,
        stop.address,
        result.lat,
        result.lng,
        result.provider,
        result.confidence,
    )
    return result.lat, result.lng, result.provider, result.confidence, False


def _get_trip(db: Session, organization_id: int, trip_id: int) -> models.Trip:
    trip = (
        db.query(models.Trip)
        .filter(
            models.Trip.id == trip_id,
            models.Trip.organization_id == organization_id,
        )
        .first()
    )
    if trip is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Viaje no encontrado"
        )
    return trip


def _trip_origin(
    db: Session, trip: models.Trip
) -> tuple[float, float] | None:
    """Desde dónde se calcula la ruta: el camión, o el depósito si no reportó.

    La posición medida manda sobre la planificada: en un viaje en curso la ruta
    útil arranca donde está el camión, no donde salió.
    """
    if trip.truck_id is not None:
        point = (
            db.query(models.TrackingPoint)
            .filter(models.TrackingPoint.truck_id == trip.truck_id)
            .order_by(*MEASUREMENT_ORDER)
            .first()
        )
        if point is not None:
            return (point.lat, point.long)
    if trip.depot_id is not None:
        depot = db.get(models.Depot, trip.depot_id)
        if depot is not None:
            return (depot.lat, depot.lng)
    return None


@router.get("", response_model=list[schemas.ChargerResponse])
def list_chargers(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Charger)
        .filter(models.Charger.organization_id == current_user.organization_id)
        .order_by(models.Charger.name)
        .all()
    )


@router.post(
    "", response_model=schemas.ChargerResponse, status_code=status.HTTP_201_CREATED
)
def create_charger(
    payload: schemas.ChargerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    charger = models.Charger(
        organization_id=current_user.organization_id,
        name=payload.name,
        contact=payload.contact,
    )
    db.add(charger)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un dador de carga con ese nombre",
        ) from None
    db.refresh(charger)
    return charger


@depots_router.get("", response_model=list[schemas.DepotResponse])
def list_depots(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Depot)
        .filter(models.Depot.organization_id == current_user.organization_id)
        .order_by(models.Depot.name)
        .all()
    )


@depots_router.post(
    "", response_model=schemas.DepotResponse, status_code=status.HTTP_201_CREATED
)
def create_depot(
    payload: schemas.DepotCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    depot = models.Depot(
        organization_id=current_user.organization_id,
        name=payload.name,
        lat=payload.lat,
        lng=payload.lng,
        radius_m=payload.radius_m,
    )
    db.add(depot)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un depósito con ese nombre",
        ) from None
    db.refresh(depot)
    return depot


OPEN_TRIP_STATUSES = ("planned", "in_progress")
# Destino de la ruta: la próxima parada sin llegar. Una parada ya alcanzada
# (`arrived`) no se vuelve a pedir: el camión ya está en su radio y lo que sigue
# es la siguiente.
ROUTE_TARGET_STATUS = "pending"


@trips_router.get("/available-trucks")
def list_available_trucks(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Camiones que pueden tomar un viaje hoy: activos y sin viaje abierto.

    El radio del depósito todavía no se chequea: depende de telemetría fresca y
    un camión sin señal quedaría excluido sin motivo. `depots.lat/lng/radius_m`
    ya existen para cuando se agregue.
    """
    busy = (
        db.query(models.Trip.truck_id)
        .filter(
            models.Trip.organization_id == current_user.organization_id,
            models.Trip.truck_id.isnot(None),
            models.Trip.status.in_(OPEN_TRIP_STATUSES),
        )
        .subquery()
    )
    trucks = (
        db.query(models.Truck)
        .filter(
            models.Truck.organization_id == current_user.organization_id,
            models.Truck.active.is_(True),
            models.Truck.id.notin_(db.query(busy.c.truck_id)),
        )
        .order_by(models.Truck.plate)
        .all()
    )
    return [{"id": truck.id, "plate": truck.plate} for truck in trucks]


@trips_router.get("", response_model=list[schemas.TripResponse])
def list_trips(
    charger_id: int | None = Query(default=None),
    truck_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    query = db.query(models.Trip).filter(
        models.Trip.organization_id == current_user.organization_id
    )
    if charger_id is not None:
        query = query.filter(models.Trip.charger_id == charger_id)
    if truck_id is not None:
        query = query.filter(models.Trip.truck_id == truck_id)
    return query.order_by(
        models.Trip.departure_at.desc(), models.Trip.id.desc()
    ).all()


@trips_router.post(
    "", response_model=schemas.TripResponse, status_code=status.HTTP_201_CREATED
)
def create_trip(
    payload: schemas.TripCreate,
    db: Session = Depends(get_db),
    geocoder: Geocoder = Depends(get_geocoder),
    current_user: models.User = Depends(require_org_admin),
):
    organization_id = current_user.organization_id

    charger = (
        db.query(models.Charger)
        .filter(
            models.Charger.id == payload.charger_id,
            models.Charger.organization_id == organization_id,
        )
        .first()
    )
    if charger is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dador de carga no encontrado"
        )

    if payload.truck_id is not None:
        truck = (
            db.query(models.Truck)
            .filter(
                models.Truck.id == payload.truck_id,
                models.Truck.organization_id == organization_id,
            )
            .first()
        )
        if truck is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Camión no encontrado"
            )
        abiertos = (
            db.query(models.Trip)
            .filter(
                models.Trip.organization_id == organization_id,
                models.Trip.truck_id == truck.id,
                models.Trip.status.in_(OPEN_TRIP_STATUSES),
            )
            .all()
        )
        if abiertos and not payload.replace_open_trip:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El camión ya tiene un viaje abierto. Mandá "
                    "`replace_open_trip: true` para reasignarlo."
                ),
            )
        for abierto in abiertos:
            # El viaje reemplazado no se borra: queda cancelado, así se ve en la
            # lista que hubo uno y que se reemplazó.
            abierto.status = "cancelled"

    depot_id = payload.depot_id
    if depot_id is not None:
        depot = (
            db.query(models.Depot)
            .filter(
                models.Depot.id == depot_id,
                models.Depot.organization_id == organization_id,
            )
            .first()
        )
        if depot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Depósito no encontrado"
            )
    else:
        # Un solo depósito por organización es el caso normal: no obligamos a
        # elegirlo en cada viaje.
        unico = (
            db.query(models.Depot)
            .filter(models.Depot.organization_id == organization_id)
            .all()
        )
        depot_id = unico[0].id if len(unico) == 1 else None

    if payload.external_ref is not None:
        existing = (
            db.query(models.Trip)
            .filter(
                models.Trip.organization_id == organization_id,
                models.Trip.external_ref == payload.external_ref,
            )
            .first()
        )
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un viaje con esa referencia externa",
            )

    trip = models.Trip(
        organization_id=organization_id,
        charger_id=charger.id,
        truck_id=payload.truck_id,
        driver_name=payload.driver_name,
        departure_at=payload.departure_at,
        depot_id=depot_id,
        external_ref=payload.external_ref,
        notes=payload.notes,
    )
    db.add(trip)
    db.flush()

    for index, stop in enumerate(payload.stops):
        lat, lng, source, confidence, needs_review = _resolve_coordinates(
            db, organization_id, stop, geocoder
        )
        db.add(
            models.TripStop(
                trip_id=trip.id,
                seq=index + 1,
                address=stop.address,
                lat=lat,
                lng=lng,
                geo_source=source,
                geo_confidence=confidence,
                needs_review=needs_review,
                receiver=stop.receiver,
            )
        )

    db.commit()
    db.refresh(trip)
    return trip


@trips_router.get("/{trip_id}", response_model=schemas.TripResponse)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return _get_trip(db, current_user.organization_id, trip_id)


@trips_router.post("/{trip_id}/reset", response_model=schemas.TripResponse)
def reset_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    """Vuelve el viaje a cero: planificado y con todas las paradas pendientes.

    Lo usan la demo y la operación cuando el camión arranca un recorrido nuevo:
    las entregas de la corrida anterior no cuentan para la nueva. No borra el
    viaje ni sus destinos, sólo su progreso.
    """
    trip = _get_trip(db, current_user.organization_id, trip_id)
    trip.status = "planned"
    for stop in trip.stops:
        stop.status = "pending"
        stop.arrived_at = None
        stop.departed_at = None
    db.commit()
    db.refresh(trip)
    return trip


@trips_router.get("/{trip_id}/route", response_model=schemas.TripRouteResponse)
def get_trip_route(
    trip_id: int,
    db: Session = Depends(get_db),
    router: Router = Depends(get_router),
    current_user: models.User = Depends(get_current_user),
):
    """Ruta por calles desde el camión hasta la próxima parada del viaje.

    Es de lectura y por eso la puede pedir un `member`: ver el recorrido no
    cambia nada. Se dibuja **sólo el tramo hasta la parada que toca**, en orden:
    el viaje es secuencial y mostrar el atajo a una parada posterior haría creer
    que se salteó una. Si el proveedor no está configurado o falla, el mapa
    vuelve a la línea recta entre destinos; nunca se inventa una geometría.
    """
    trip = _get_trip(db, current_user.organization_id, trip_id)

    origin = _trip_origin(db, trip)
    if origin is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "El viaje no tiene origen: el camión no reportó posición y no "
                "hay depósito asignado"
            ),
        )

    next_stop: models.TripStop | None = None
    destination: tuple[float, float] | None = None
    for stop in trip.stops:
        if (
            stop.status == ROUTE_TARGET_STATUS
            and stop.lat is not None
            and stop.lng is not None
        ):
            next_stop = stop
            destination = (stop.lat, stop.lng)
            break

    if next_stop is None or destination is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El viaje no tiene paradas pendientes con coordenada",
        )

    if router.name == "none":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El ruteo no está configurado (ROUTING_PROVIDER)",
        )

    result = router.route([origin, destination])
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo calcular la ruta con el proveedor de ruteo",
        )

    return {
        "trip_id": trip.id,
        "stop_id": next_stop.id,
        "stop_seq": next_stop.seq,
        "provider": result.provider,
        "distance_m": result.distance_m,
        "duration_s": result.duration_s,
        "geometry": [[lat, lng] for lat, lng in result.points],
    }


@trips_router.patch(
    "/{trip_id}/stops/{stop_id}",
    response_model=schemas.StopResponse,
)
def resolve_stop(
    trip_id: int,
    stop_id: int,
    payload: schemas.StopCoordinates,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    """Pin manual: resuelve el destino y deja la dirección en caché.

    Es el plan B obligatorio del flujo: ninguna dirección rural ni informal
    geocodifica, y sin esto la importación queda trabada.
    """
    trip = _get_trip(db, current_user.organization_id, trip_id)
    stop = (
        db.query(models.TripStop)
        .filter(models.TripStop.id == stop_id, models.TripStop.trip_id == trip.id)
        .first()
    )
    if stop is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Destino no encontrado"
        )

    stop.lat = payload.lat
    stop.lng = payload.lng
    stop.geo_source = MANUAL
    stop.geo_confidence = 1.0
    stop.needs_review = False
    _store_cache(
        db,
        trip.organization_id,
        stop.address,
        payload.lat,
        payload.lng,
        MANUAL,
        confidence=1.0,
        user_id=current_user.id,
    )
    db.commit()
    db.refresh(stop)
    return stop


@destinations_router.get("/pending", response_model=list[schemas.StopResponse])
def list_pending_stops(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Cola de revisión: destinos que no tienen coordenada."""
    return (
        db.query(models.TripStop)
        .join(models.Trip, models.Trip.id == models.TripStop.trip_id)
        .filter(
            models.Trip.organization_id == current_user.organization_id,
            models.TripStop.needs_review.is_(True),
        )
        .order_by(models.Trip.departure_at, models.TripStop.seq)
        .all()
    )
