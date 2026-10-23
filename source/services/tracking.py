from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db
from source.schemas.truck import TruckActive, TruckReassign
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

def _persist_truck(
    db: Session,
    truck: schemas.Truck,
    location: schemas.Location,
    organization_id: int,
) -> None:
    """Create a truck and its first tracking point for an explicit organization."""
    if db.query(models.Truck).filter(models.Truck.id == truck.id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El camión ya existe")
    if db.query(models.Truck).filter(models.Truck.plate == truck.plate).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La patente ya existe")

    db.add(models.Truck(id=truck.id, plate=truck.plate, organization_id=organization_id))
    db.add(
        models.TrackingPoint(
            truck_id=truck.id,
            lat=location.lat,
            long=location.long,
            speed=location.speed,
            heading=location.heading,
            recorded_at=location.recorded_at or datetime.now(UTC),
        )
    )
    db.commit()


#agrega un camión a la base de datos
@router.post("")
def add_truck(
    truck: schemas.Truck,
    location: schemas.Location,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_org_admin),
):
    _persist_truck(db, truck, location, current_user.organization_id)
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }


@org_router.post("/{organization_id}/trucks")
def add_truck_for_organization(
    organization_id: int,
    truck: schemas.Truck,
    location: schemas.Location,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(require_platform_admin),
):
    """Platform onboarding: provision a truck inside any organization."""
    organization = db.get(models.Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada"
        )
    _persist_truck(db, truck, location, organization.id)
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
    db.commit()
    db.refresh(truck)
    return {
        "mensaje": "Camión reasignado a nueva organización",
        "truck_id": truck.id,
        "organization_id": truck.organization_id,
    }

#Agrega un punto de ubicación al historial del camión
@router.put("/{truck_id}/location")
def update_location(truck_id: int, location: schemas.Location, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="camión no encontrado"
            )
    if not truck.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El camión está inactivo",
        )
    db_point = models.TrackingPoint(
        truck_id=truck_id,
        lat=location.lat,
        long=location.long,
        speed=location.speed,
        heading=location.heading,
        recorded_at=location.recorded_at or datetime.now(UTC),
    )
    #Cada actualización se agrega como un nuevo punto de tracking.
    db.add(db_point)
    db.commit()
    return{"mensaje": "Ubicación actualizada correctamente"}

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
