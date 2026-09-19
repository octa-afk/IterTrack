from pydantic import BaseModel, Field
from datetime import datetime

#camion con id
class Truck(BaseModel):
        id: int
        plate: str

#ubicacion
class Location(BaseModel):
        lat: float
        long: float
        
#historial con Truck e historial de ubicaciones
class TrackingPoint(BaseModel):
        truck_id: int
        location: Location
        timestamp: datetime = Field(default_factory=datetime.now)

        
