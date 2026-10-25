from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DepotCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=120)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    radius_m: int = Field(default=150, ge=10, le=5000)


class DepotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lat: float
    lng: float
    radius_m: int


class ChargerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=2, max_length=120)
    contact: str | None = Field(default=None, max_length=120)


class ChargerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact: str | None
    active: bool


class StopCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    address: str = Field(..., min_length=3, max_length=300)
    receiver: str | None = Field(default=None, max_length=120)
    # El dador puede mandar la coordenada ya resuelta; si viene, se usa tal cual
    # y no se consulta al geocoder. Las dos o ninguna.
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def require_both_coordinates(self) -> "StopCreate":
        if (self.lat is None) != (self.lng is None):
            raise ValueError("lat y lng deben venir juntas o no venir")
        return self


class TripCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    charger_id: int
    departure_at: datetime
    external_ref: str | None = Field(default=None, max_length=64)
    truck_id: int | None = None
    depot_id: int | None = None
    # Un camión puede tener otro viaje abierto. Sin este permiso explícito la
    # creación falla: cancelar el viaje de otro sin avisar sería una sorpresa.
    replace_open_trip: bool = False
    driver_name: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    stops: list[StopCreate] = Field(..., min_length=1, max_length=200)

    @field_validator("departure_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        """Sin zona, "07:30" puede ser Córdoba o UTC y la salida se corre 3 h."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("departure_at must include timezone")
        return value


class StopResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seq: int
    address: str
    lat: float | None
    lng: float | None
    geo_source: str | None
    geo_confidence: float | None
    needs_review: bool
    receiver: str | None
    status: str


class TripResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    charger_id: int
    truck_id: int | None
    driver_name: str | None
    departure_at: datetime
    depot_id: int | None
    status: str
    external_ref: str | None
    notes: str | None
    created_at: datetime
    stops: list[StopResponse]


class StopCoordinates(BaseModel):
    """Pin manual: resuelve un destino que el geocoder no pudo ubicar."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class TripRouteResponse(BaseModel):
    """Ruta por calles hasta la próxima parada del viaje.

    `geometry` va en pares [lat, lng] y en orden de recorrido: el mapa dibuja
    exactamente lo que recibe, sin reinterpretar el formato de OSRM. `stop_id` y
    `stop_seq` identifican el destino: el viaje es secuencial y sólo se dibuja
    el tramo que falta hasta la parada que toca.
    """

    trip_id: int
    stop_id: int
    stop_seq: int
    provider: str
    distance_m: float
    duration_s: float
    geometry: list[list[float]]
