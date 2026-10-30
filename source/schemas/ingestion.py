from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceIngestPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sequence: int = Field(ge=0)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed: float = Field(ge=0)
    heading: float = Field(ge=0, le=360)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("recorded_at must include timezone")
        if value > datetime.now(UTC) + timedelta(seconds=60):
            raise ValueError("recorded_at cannot be in the future")
        return value.astimezone(UTC)

    @field_validator("heading")
    @classmethod
    def normalize_heading(cls, value: float) -> float:
        return 0 if value == 360 else value


class DeviceIngestBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: Literal[1] = 1
    batch_id: UUID
    points: list[Any] = Field(min_length=1, max_length=100)
