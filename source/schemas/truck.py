from datetime import datetime
from typing import Literal

from pydantic import BaseModel


#camion con id
class Truck(BaseModel):
        id: int
        plate: str

class TruckActive(BaseModel):
        active: bool

class TruckReassign(BaseModel):
        organization_id: int


class TruckLive(BaseModel):
    """Estado actual de un camión: la foto de la flota que pide el mapa.

    Sale de `GET /trucks/live`. La posición, la velocidad y el rumbo son los del
    último punto medido (`recorded_at`), tal como los informó el equipo. El
    estado lo calcula el servidor con su reloj, para que no dependa de la hora
    de la computadora de quien mira. Un camión que nunca reportó viene con la
    posición en `null` y estado `stop`.
    """

    id: int
    plate: str
    active: bool
    lat: float | None
    lng: float | None
    speed: float | None
    heading: float | None
    recorded_at: datetime | None
    status: Literal["move", "idle", "stop", "alert"]
