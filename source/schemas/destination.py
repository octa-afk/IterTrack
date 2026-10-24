from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    scheduled_for: date
    external_ref: str | None = Field(default=None, max_length=64)
    truck_id: int | None = None
    driver_name: str | None = Field(default=None, max_length=120)
    notes: str | None = None
    stops: list[StopCreate] = Field(..., min_length=1, max_length=200)


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
    scheduled_for: date
    status: str
    external_ref: str | None
    notes: str | None
    created_at: datetime
    stops: list[StopResponse]


class StopCoordinates(BaseModel):
    """Pin manual: resuelve un destino que el geocoder no pudo ubicar."""

    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
