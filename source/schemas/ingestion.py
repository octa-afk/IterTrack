from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceIngestPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    lat: float = Field(ge=-90, le=90)
    long: float = Field(ge=-180, le=180)
    speed: float = Field(ge=0)
    heading: float = Field(ge=0, le=360)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include timezone")
        return value


class DeviceIngestBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: UUID
    points: list[Any] = Field(min_length=1, max_length=100)
