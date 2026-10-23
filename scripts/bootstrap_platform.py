"""One-time platform bootstrap: the internal organization and its first owner.

This is the account the platform team owns. It is created once per deployment
and never touched by the demo reset, which is why it lives in its own script.

Usage:
    env/bin/python -m scripts.bootstrap_platform

Required environment variables (see .env.example):
    PLATFORM_ADMIN_USERNAME, PLATFORM_ADMIN_EMAIL, PLATFORM_ADMIN_PASSWORD
"""

import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from source.database.database import SessionLocal
from source.models.organization import Organization
from source.models.user import ROLE_PLATFORM_ADMIN, User
from source.services.auth import hash_password

MIN_PASSWORD_LENGTH = 12
DEFAULT_ORG_NAME = "IterTrack"


class BootstrapError(ValueError):
    """Configuration or state problem that prevents bootstrapping."""


@dataclass(frozen=True)
class PlatformBootstrapConfig:
    org_name: str
    username: str
    email: str
    full_name: str
    password: str


@dataclass(frozen=True)
class BootstrapResult:
    organization_created: bool
    user_created: bool
    organization_id: int
    username: str


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise BootstrapError(f"Falta la variable de entorno {name}.")
    return value


def config_from_env() -> PlatformBootstrapConfig:
    password = _required("PLATFORM_ADMIN_PASSWORD")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise BootstrapError(
            f"PLATFORM_ADMIN_PASSWORD debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    return PlatformBootstrapConfig(
        org_name=os.getenv("PLATFORM_ORG_NAME", DEFAULT_ORG_NAME).strip() or DEFAULT_ORG_NAME,
        username=_required("PLATFORM_ADMIN_USERNAME"),
        email=_required("PLATFORM_ADMIN_EMAIL"),
        full_name=os.getenv("PLATFORM_ADMIN_FULL_NAME", "Platform Owner").strip()
        or "Platform Owner",
        password=password,
    )


def bootstrap_platform(db: Session, config: PlatformBootstrapConfig) -> BootstrapResult:
    """Create the internal organization and its platform owner, idempotently."""
    if len(config.password) < MIN_PASSWORD_LENGTH:
        raise BootstrapError(
            f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )

    organization = (
        db.query(Organization).filter(Organization.name == config.org_name).first()
    )
    organization_created = organization is None
    if organization is None:
        organization = Organization(
            name=config.org_name,
            invitation_code=secrets.token_urlsafe(12),
            invitation_expires_at=None,
            invitation_revoked_at=datetime.now(UTC),
        )
        db.add(organization)
        db.flush()

    user = db.query(User).filter(User.username == config.username).first()
    user_created = user is None
    if user is None:
        user = User(
            username=config.username,
            email=config.email,
            full_name=config.full_name,
            hashed_password=hash_password(config.password),
            organization_id=organization.id,
            role=ROLE_PLATFORM_ADMIN,
        )
        db.add(user)
    else:
        # Re-running must converge: an existing account is promoted, never duplicated.
        user.role = ROLE_PLATFORM_ADMIN
        user.organization_id = organization.id

    db.commit()
    db.refresh(organization)
    db.refresh(user)
    return BootstrapResult(
        organization_created=organization_created,
        user_created=user_created,
        organization_id=organization.id,
        username=user.username,
    )


def main() -> int:
    try:
        config = config_from_env()
    except BootstrapError as error:
        print(f"⛔ {error}")
        return 1

    with SessionLocal() as db:
        result = bootstrap_platform(db, config)

    estado_org = "creada" if result.organization_created else "ya existía"
    estado_user = "creado" if result.user_created else "ya existía (rol convergido)"
    print(f"🏢 Organización '{config.org_name}': {estado_org} (id {result.organization_id})")
    print(f"👑 platform_admin '{result.username}': {estado_user}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
