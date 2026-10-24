from pydantic import BaseModel


#camion con id
class Truck(BaseModel):
        id: int
        plate: str

class TruckActive(BaseModel):
        active: bool

class TruckReassign(BaseModel):
        organization_id: int
