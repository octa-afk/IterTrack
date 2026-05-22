from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
        return "Itertrack in the house 😎💯🚚"

#camion con id y coordenadas
class Truck(BaseModel):
        id: int
        
class Location(BaseModel):
        lat: float
        long: float
        
#historial con Truck e historial de ubicaciones
class History(BaseModel):
        order: int
        truck: Truck

#
truck_db = {} 

current_location = {}

history = []

@app.post("/trucks")
def add_truck(truck: Truck, location: Location):
    truck_db[truck.id] = {
        "lat": location.lat,
        "long": location.long,
        "timestamp": datetime.now() 
    }    
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }

#actualiza la ubiación actual del camión
@app.put("/trucks/{truck_id}/location")
def update_location(truck: Truck, location: Location):
    if truck.id not in truck_db:
        return{
            "error": "Camión no encontrado"
        }
    truck_db[truck.id] = {
        "lat": location.lat,
        "long": location.long,
        "timestamp": datetime.now() 
    }
    #datetime corre en el servidor, no es la hora en la que fue medida la ubicaci
    return{
        "mensaje": "Ubicación actualizada"
        }

@app.put("/trucks/{truck_id}/iter")

@app.get("/trucks/{truck_id}")
def get_truck(truck_id: int):
    if truck_id not in truck_db:
        return {
            "error": "Camión no encontrado"
        }
    return truck_db[truck_id]

@app.get("/trucks")
def get_truck_db():
    return truck_db

