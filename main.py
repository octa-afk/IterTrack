from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

@app.get("/")
async def root():
        return "Itertrack in the house 😎💯🚚"

class Truck(BaseModel):
        id: int
        lat: float
        long: float
        
truck_db = {} 

current_location = {}
history_location = {}

@app.post("/trucks")
def add_truck(truck: Truck):
    truck_db[truck.id] = {
        "lat": 0,
        "long": 0,
        "dt": 0
    }
    
    return {
        "mensaje": "Camión agregado",
        "truck": truck
    }

#actualiza la ubiación actual del camión
@app.put("/trucks")
def update_location(truck: Truck):
    if truck.id not in truck_db:
        return{
            "error": "Camión no encontrado"
        }

    truck_db[truck.id] = {
        "lat": truck.lat,
        "long": truck.long,
        "dt": datetime.now() 
    }
    #datetime corre en el servidor, no es la hora en la que fue medida la ubicaci
    return{
        "mensaje": "Ubicación actualizada"
        }

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

