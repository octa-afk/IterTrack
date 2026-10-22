import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=12, description="Mínimo 12 carácteres")
    invitation_code: str | None = None
    org_name: str | None = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("La contraseña debe contener al menos una letra")
        if not re.search(r"\d", v):
            raise ValueError("La contraseña debe contener al menos un número")
        return v



class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str
    disabled: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str
