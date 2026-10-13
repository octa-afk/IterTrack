from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db
from source.services.auth import get_current_user

router = APIRouter(prefix="/trucks", tags=["trucks"])

#agrega un camión a la base de datos
@router.post("")
def add_truck(truck: schemas.Truck, location: schemas.Location, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if db.query(models.Truck).filter(models.Truck.id == truck.id).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El camión ya existe")
    if db.query(models.Truck).filter(models.Truck.plate == truck.plate).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La patente ya existe")
    db_truck = models.Truck(id=truck.id, plate=truck.plate, organization_id=current_user.organization_id)
    db.add(db_truck)

    db_tracking_point = models.TrackingPoint(
        truck_id=truck.id,
        lat=location.lat,
        long=location.long,
        speed=location.speed,
        heading=location.heading,
        recorded_at=location.recorded_at or datetime.now(timezone.utc),
    )
    db.add(db_tracking_point)

    db.commit()
    return {
        "mensaje": "Camión agregado",
        "truck": truck
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
    db_point = models.TrackingPoint(
        truck_id=truck_id,
        lat=location.lat,
        long=location.long,
        speed=location.speed,
        heading=location.heading,
        recorded_at=location.recorded_at or datetime.now(timezone.utc),
    )
    #Cada actualización se agrega como un nuevo punto de tracking.
    db.add(db_point)
    db.commit()
    return{"mensaje": "Ubicación actualizada correctamente"}

#Devuelve el punto de tracking más reciente del camión
@router.get("/{truck_id}/location")
def get_latest_truck_location(truck_id: int, db: Session=Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
            raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="camión no encontrado"
            )
    latest_point = (db.query(models.TrackingPoint).filter(models.TrackingPoint.truck_id==truck_id).order_by(models.TrackingPoint.timestamp.desc()).first()
    )
    
    if not latest_point:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="El camión no tiene ubicaciones registradas"
         )

    return latest_point

#Devuelve hasta 100 puntos de tracking, del más nuevo al más antiguo
@router.get("/{truck_id}/iter")
def get_history_truck(truck_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    truck=db.query(models.Truck).filter(models.Truck.id==truck_id).first()
    if not truck or truck.organization_id != current_user.organization_id:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="camión no encontrado"
         )
    locations = (
         db.query(models.TrackingPoint)
         .filter(models.TrackingPoint.truck_id==truck_id)
         .order_by(models.TrackingPoint.timestamp.desc())
         .limit(100)
         .all()
    )

    return locations

#Borra los puntos de tracking del camión sin eliminar el camión
@router.delete("/{truck_id}/iter", status_code=status.HTTP_204_NO_CONTENT)
def delete_truck_iter(truck_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
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
