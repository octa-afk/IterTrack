from pydantic import BaseModel

#camion con id
class Truck(BaseModel):
        id: int

#ubicacion
class Location(BaseModel):
        lat: float
        long: float
        
#historial con Truck e historial de ubicaciones
class History(BaseModel):
        order: int
        truck: Truck
