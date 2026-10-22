from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field, field_validator


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
        # Momento de medición informado por el emisor. Si no se envía, el servidor usa su hora.
        recorded_at: datetime | None = None

        @field_validator("recorded_at")
        @classmethod
        def validate_recorded_at(cls, value: datetime | None) -> datetime | None:
            if value is None:
                return value
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("recorded_at debe incluir zona horaria")
            # Tolerancia pequeña por desfasaje de relojes entre emisor y servidor.
            if value > datetime.now(UTC) + timedelta(seconds=60):
                raise ValueError("recorded_at no puede estar en el futuro")
            return value.astimezone(UTC)

        @field_validator("heading")
        @classmethod
        def normalize_heading(cls, value: float) -> float:
            return 0 if value == 360 else value
#historial con Truck e historial de ubicaciones
class TrackingPoint(BaseModel):
        truck_id: int
        location: Location
        timestamp: datetime = Field(default_factory=datetime.now)
