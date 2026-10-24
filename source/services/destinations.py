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
