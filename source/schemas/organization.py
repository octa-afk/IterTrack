from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    # Null means the invitation never expires.
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)

    model_config = {"str_strip_whitespace": True}


class InvitationRotate(BaseModel):
    expires_in_days: int | None = Field(default=None, ge=1, le=3650)


class OrganizationResponse(BaseModel):
    id: int
    name: str
    invitation_code: str
    invitation_expires_at: datetime | None
    invitation_revoked_at: datetime | None
    invitation_active: bool

    model_config = {"from_attributes": True}
