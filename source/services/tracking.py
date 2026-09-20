from fastapi import APIRouter, Depends
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
def update_location(truck_id: int, location: Location):
    if truck_id not in truck_db:
        return {
            "error": "Camión no encontrado"
        }
    current_location_db[truck_id] = location
    #actualiza el recorrido del camión
    history_db.append(TrackingPoint (truck_id = truck_id, location = location))
    return {
        "mensaje": "Ubicación actualizada"
    }

#devuelve la ubicación actual del camion
@router.get("/{truck_id}/location")
def get_truck_location(truck_id: int):
    if truck_id not in truck_db:
        return {
            "error": "Camión no encontrado"
        }
    return current_location_db[truck_id]

#devuelve todas las ubicaciones de un camión
@router.get("/{truck_id}/iter")
def get_history_truck(truck_id: int, ):
    if truck_id not in truck_db:
        return {
            "error": "Camión no encontrado"
        }
    #history hace referencia a las ultimas 10 ubicaciones
    history = [
        tp for tp in history_db
        if tp.truck_id == truck_id
    ]

    return history[-10:]
    

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