from pydantic import BaseModel, Field
from datetime import datetime

#camion con id
class Truck(BaseModel):
        id: int
        plate: str

#ubicacion
class Location(BaseModel):
        lat: float = Field(ge=-90, le=90)
        long: float = Field(ge=-180, le=180)
        speed: float = Field(default=0, ge=0)
        heading: float = Field(default=0, ge=0, le=360)
#historial con Truck e historial de ubicaciones
class TrackingPoint(BaseModel):
        truck_id: int
        location: Location
        timestamp: datetime = Field(default_factory=datetime.now)
