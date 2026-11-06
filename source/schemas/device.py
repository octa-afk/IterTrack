from datetime import datetime

from pydantic import BaseModel, Field


class DeviceCreate(BaseModel):
    identifier: str = Field(..., min_length=1, max_length=64)
    truck_id: int

    model_config = {"str_strip_whitespace": True}


class DeviceReassign(BaseModel):
    truck_id: int


class DeviceAssignmentInfo(BaseModel):
    truck_id: int
    valid_from: datetime


class DeviceResponse(BaseModel):
    id: int
    identifier: str
    active: bool
    organization_id: int | None = None
    assignment: DeviceAssignmentInfo | None


class DeviceProvisioned(DeviceResponse):
    """A device plus its plaintext token, returned only on creation and rotation."""

    token: str
