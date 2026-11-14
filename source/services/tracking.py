
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db
from source.schemas.truck import TruckActive, TruckLive, TruckReassign
from source.services.auth import (
    get_current_user,
    require_org_admin,
    require_platform_admin,
)

router = APIRouter(prefix="/trucks", tags=["trucks"])

# Trucks are provisioned by the platform on behalf of a customer, so onboarding
# lives under the organization it belongs to instead of an optional body field.
org_router = APIRouter(prefix="/organizations", tags=["trucks"])

# Lectura ordenada por hora de medición (recorded_at), más nuevo primero; id desempata mediciones iguales.
MEASUREMENT_ORDER = (models.TrackingPoint.recorded_at.desc(), models.TrackingPoint.id.desc())

# Reglas del estado de un camión en el mapa. Sin reporte en 10 minutos se lo da
# por apagado; arriba de 90 km/h es una alerta; debajo de 3 km/h, el ruido del
# GPS de un camión parado.
STALE_AFTER = timedelta(minutes=10)
SPEED_LIMIT_KMH = 90
IDLE_BELOW_KMH = 3

def _persist_truck(
    db: Session,
    truck: schemas.Truck,
    organization_id: int,
) -> None:
    """Create a truck for an explicit organization.

    No tracking point is written: telemetry only enters through
    `POST /devices/ingest`, authenticated with the device credential. A freshly
    created truck has no position until its device reports one.
    """
    if db.query(models.Truck).filter(models.Truck.id == truck.id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El camión ya existe")
    if db.query(models.Truck).filter(models.Truck.plate == truck.plate).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La patente ya existe")

    db.add(models.Truck(id=truck.id, plate=truck.plate, organization_id=organization_id))
    db.commit()


#agrega un camión a la base de datos
@router.post("")
def add_truck(
    truck: schemas.Truck,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    _persist_truck(db, truck, current_user.organization_id)
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }


@org_router.post("/{organization_id}/trucks")
def add_truck_for_organization(
    organization_id: int,
    truck: schemas.Truck,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_platform_admin),
):
    """Platform onboarding: provision a truck inside any organization."""
    organization = db.get(models.Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada"
        )
    _persist_truck(db, truck, organization.id)
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }

# Cambia el estado activo/inactivo de un camión. Solo administradores.
@router.patch("/{truck_id}/activate")
def activate_truck(
    truck_id: int,
    payload: TruckActive,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    truck = (
        db.query(models.Truck)
        .filter(
            models.Truck.id == truck_id,
            models.Truck.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not truck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camión no encontrado",
        )
    truck.active = payload.active
    db.commit()
    db.refresh(truck)
    return {
        "mensaje": f"Camión {'activado' if payload.active else 'desactivado'}",
        "truck_id": truck.id,
        "active": truck.active,
    }

# Reasigna un camión a otra organización. Solo el administrador de plataforma,
# porque transferir un activo entre empresas no es una decisión del cliente.
@router.patch("/{truck_id}/organization")
def reassign_truck_organization(
    truck_id: int,
    payload: TruckReassign,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_platform_admin),
):
    truck = db.get(models.Truck, truck_id)
    if not truck:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camión no encontrado",
        )

    org = (
        db.query(models.Organization)
        .filter(models.Organization.id == payload.organization_id)
        .first()
    )
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organización destino no encontrada",
        )
    truck.organization_id = payload.organization_id
    # Devices assigned to the truck move with it. Without this the previous
    # tenant still owns (and can revoke) a device that now serves another
    # organization, while the new tenant cannot manage it at all.
    assigned_devices = (
        db.query(models.Device)
        .join(models.DeviceAssignment, models.DeviceAssignment.device_id == models.Device.id)
        .filter(
            models.DeviceAssignment.truck_id == truck.id,
            models.DeviceAssignment.valid_to.is_(None),
        )
        .all()
    )
    for device in assigned_devices:
        device.organization_id = payload.organization_id
    db.commit()
    db.refresh(truck)
    return {
        "mensaje": "Camión reasignado a nueva organización",
        "truck_id": truck.id,
        "organization_id": truck.organization_id,
    }

#Devuelve el punto de tracking más reciente del camión, según recorded_at (hora de medición)
@router.get("/{truck_id}/location")
def get_latest_truck_location(truck_id: int, db: Session=Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
            raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="camión no encontrado"
            )
    latest_point = (db.query(models.TrackingPoint).filter(models.TrackingPoint.truck_id==truck_id).order_by(*MEASUREMENT_ORDER).first()
    )

    if not latest_point:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="El camión no tiene ubicaciones registradas"
         )

    return latest_point

#Devuelve hasta 100 puntos de tracking, del más nuevo al más antiguo según recorded_at
@router.get("/{truck_id}/iter")
def get_history_truck(truck_id: int, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck=db.query(models.Truck).filter(models.Truck.id==truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="camión no encontrado"
         )
    locations = (
         db.query(models.TrackingPoint)
         .filter(models.TrackingPoint.truck_id==truck_id)
         .order_by(*MEASUREMENT_ORDER)
         .limit(limit)
         .all()
    )

    return locations

#Borra los puntos de tracking del camión sin eliminar el camión
@router.delete("/{truck_id}/iter", status_code=status.HTTP_204_NO_CONTENT)
def delete_truck_iter(truck_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_org_admin)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="camión no encontrado"
        )
    db.query(models.TrackingPoint).filter(
        models.TrackingPoint.truck_id == truck_id
    ).delete()
    db.commit()
    return None


def _as_utc(moment: datetime) -> datetime:
    """SQLite no conserva la zona horaria aunque la columna la declare.

    Sin esto la respuesta sale sin zona y el navegador la lee como hora local:
    en Argentina el camión aparecería con tres horas de atraso.
    """
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)


def truck_status(point: models.TrackingPoint | None, now: datetime) -> str:
    """`move`, `idle`, `stop` o `alert` según el último punto medido."""
    if point is None:
        return "stop"
    if now - _as_utc(point.recorded_at) > STALE_AFTER:
        return "stop"
    if point.speed > SPEED_LIMIT_KMH:
        return "alert"
    if point.speed < IDLE_BELOW_KMH:
        return "idle"
    return "move"


@router.get("/live", response_model=list[TruckLive])
def get_trucks_live(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """La flota en un solo pedido: cada camión con su último punto medido.

    Reemplaza el `GET /trucks/{id}/location` por camión que el mapa hacía en
    cada latido (1 + N pedidos cada 3 s por usuario). El último punto sale de
    una subconsulta correlacionada con `LIMIT 1`, que usa el índice
    `(truck_id, recorded_at desc, id desc)`: el costo crece con la cantidad de
    camiones, no con el historial acumulado.
    """
    point = models.TrackingPoint
    latest_id = (
        select(point.id)
        .where(point.truck_id == models.Truck.id)
        .order_by(*MEASUREMENT_ORDER)
        .limit(1)
        .correlate(models.Truck)
        .scalar_subquery()
    )
    rows = db.execute(
        select(models.Truck, point)
        .outerjoin(point, point.id == latest_id)
        .where(models.Truck.organization_id == current_user.organization_id)
        .order_by(models.Truck.id)
    ).all()

    now = datetime.now(UTC)
    return [
        TruckLive(
            id=truck.id,
            plate=truck.plate,
            active=truck.active,
            lat=last.lat if last else None,
            lng=last.long if last else None,
            speed=last.speed if last else None,
            heading=last.heading if last else None,
            recorded_at=_as_utc(last.recorded_at) if last else None,
            status=truck_status(last, now),
        )
        for truck, last in rows
    ]


#devuelve el listado de todos los camiones
@router.get("")
def get_trucks(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck_list = db.query(models.Truck).filter(models.Truck.organization_id == current_user.organization_id).all()
    return truck_list

#devuelve el listado de ids y sus respectivas patentes de los camiones registrados
@router.get("/ids")
def get_truck_ids(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck_list = db.query(models.Truck.id, models.Truck.plate).filter(models.Truck.organization_id == current_user.organization_id).all()
    return [{"id": row.id, "plate": row.plate} for row in truck_list]
