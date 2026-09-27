from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db

router = APIRouter(prefix="/trucks", tags=["trucks"])

#agrega un camión a la base de datos
@router.post("")
def add_truck(truck: schemas.Truck, location: schemas.Location, db: Session = Depends(get_db)):
    if db.query(models.Truck).filter(models.Truck.id == truck.id).first():
        return {
            "error": "El camión ya existe"
        }
    if db.query(models.Truck).filter(models.Truck.plate == truck.plate).first():
        return {
            "error": "La patente ya existe"
        }
    db_truck = models.Truck(id=truck.id, plate=truck.plate)
    db.add(db_truck)

    db_tracking_point = models.TrackingPoint(truck_id=truck.id, lat=location.lat, long=location.long)
    db.add(db_tracking_point)

    db.commit()
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }

#actualiza la ubicación actual del camión
@router.put("/{truck_id}/location")
def update_location(truck_id: int, location: schemas.Location, db: Session = Depends(get_db)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first
    if not truck:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="camión no encontrado"
            )
    db_point = models.TrackingPoint(truck_id=truck_id,lat=location.lat,long=location.long)
    #actualiza el recorrido del camión
    db.add(db_point)
    db.commit()
    return{"mensaje": "Ubicación actualizada correctamente"}

#devuelve la ubicación actual del camion
@router.get("/{truck_id}/location")
def get_latest_truck_location(truck_id: int, db: Session=Depends(get_db)):
    truck = db.query(models.Truck).filter(models.Truck.id == truck_id).first()
    if not truck:
            raise HTTPException(
                 status_code=status.HTTP_404_NOT_FOUND,
                 detail="camión no encontrado"
            )
    latest_point = (db.query(models.TrackingPoint).filter(models.TrackingPoint.truck_id==truck_id).order_by(models.TrackingPoint.timestamp.desc()).first
    )
    
    if not latest_point:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND
              detail="El camión no tiene ubicaciones registradas"
         )

    return latest_point

#devuelve todas las ubicaciones de un camión
@router.get("/{truck_id}/iter")
def get_history_truck(truck_id: int, db: Session = Depends(get_db)):
    truck=db.query/(models.Truck).filter(models.Truck.id==truck_id).first()
    if not truck:
         raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail="camión no encontrado"
         )
    locations = (
         db.query(models.TrackingPoint)
         .filter(models.TrackingPoint.truck_id==truck_id)
         .order_by(models.TrackingPoint.timestamp.desc())
         .limit(100)
    )

    return locations
    

#devuelve el listado de todos los camiones
@router.get("")
def get_trucks():
    return list(truck_db.values())

#devuelve el listado de ids de camiones registrados
@router.get("/ids")
def get_truck_ids():
    return list(truck_db)

#busca un camión por patente
@router.get("/plate/{plate}")
def get_truck_by_plate(plate: str):
    for truck in truck_db.values():
        if truck.plate == plate:
            return truck
    return {
        "error": "Camión no encontrado"
    }