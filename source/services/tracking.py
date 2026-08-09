from fastapi import APIRouter
from app.models.truck import Truck, Location, TrackingPoint
from app.database.database import truck_db, current_location_db, history_db

router = APIRouter(prefix="/trucks", tags=["trucks"])

#agrega un camión a la base de datos
@router.post("")
def add_truck(truck: Truck, location: Location):
    if truck.id in truck_db:
        return {
            "error": "El camión ya existe"
        }
    truck_db[truck.id] = truck
    current_location_db[truck.id] = location
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