"""Administrative organization and invitation management.

Administrators are internal company staff, so every administrator can manage
every organization. Invitations are a single rotating code per organization.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from source import models, schemas
from source.database.database import get_db
from source.services.auth import get_current_admin_user

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _generate_code() -> str:
    # token_urlsafe(12) yields 16 characters, within String(20).
    return secrets.token_urlsafe(12)


def _expires_at(days: int | None) -> datetime | None:
    if days is None:
        return None
    return datetime.now(UTC) + timedelta(days=days)


def _get_organization(db: Session, organization_id: int) -> models.Organization:
    organization = db.get(models.Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organización no encontrada"
        )
    return organization


@router.get("", response_model=list[schemas.OrganizationResponse])
def list_organizations(
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin_user),
):
    return db.query(models.Organization).order_by(models.Organization.id).all()


@router.post(
    "", response_model=schemas.OrganizationResponse, status_code=status.HTTP_201_CREATED
)
def create_organization(
    payload: schemas.OrganizationCreate,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin_user),
):
    if db.query(models.Organization).filter(models.Organization.name == payload.name).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una organización con ese nombre",
        )
    organization = models.Organization(
        name=payload.name,
        invitation_code=_generate_code(),
        invitation_expires_at=_expires_at(payload.expires_in_days),
    )
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


@router.get("/{organization_id}/invitation", response_model=schemas.OrganizationResponse)
def read_invitation(
    organization_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin_user),
):
    return _get_organization(db, organization_id)


@router.post(
    "/{organization_id}/invitation/rotate",
    response_model=schemas.OrganizationResponse,
)
def rotate_invitation(
    organization_id: int,
    payload: schemas.InvitationRotate,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin_user),
):
    organization = _get_organization(db, organization_id)
    organization.invitation_code = _generate_code()
    organization.invitation_revoked_at = None
    organization.invitation_expires_at = _expires_at(payload.expires_in_days)
    db.commit()
    db.refresh(organization)
    return organization


@router.delete("/{organization_id}/invitation", response_model=schemas.OrganizationResponse)
def revoke_invitation(
    organization_id: int,
    db: Session = Depends(get_db),
    _current_user: models.User = Depends(get_current_admin_user),
):
    organization = _get_organization(db, organization_id)
    organization.invitation_revoked_at = datetime.now(UTC)
    db.commit()
    db.refresh(organization)
    return organization
