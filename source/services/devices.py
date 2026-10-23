import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from source.database.database import get_db
from source.models.device import Device, DeviceAssignment
from source.models.ingestion import IngestedPoint, RejectedIngestPoint
from source.models.truck import TrackingPoint, Truck
from source.models.user import ROLE_PLATFORM_ADMIN, User
from source.schemas.device import (
    DeviceAssignmentInfo,
    DeviceCreate,
    DeviceProvisioned,
    DeviceReassign,
    DeviceResponse,
)
from source.schemas.ingestion import DeviceIngestBatch, DeviceIngestPoint
from source.services.auth import require_org_admin, require_org_admin_or_platform

router = APIRouter(prefix="/devices", tags=["devices"])
device_bearer = HTTPBearer(auto_error=False)


class DeviceError(ValueError):
    """Domain error that the API maps to an HTTP status code."""

    status_code = status.HTTP_400_BAD_REQUEST


class DeviceNotFoundError(DeviceError):
    status_code = status.HTTP_404_NOT_FOUND


def generate_device_token() -> str:
    """Return a new random device token (shown once, never stored in plaintext)."""
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    """Hash a device token with SHA-256. Tokens are high-entropy, so no bcrypt is needed."""
    return hashlib.sha256(token.encode()).hexdigest()


def open_assignment_for(db: Session, device_id: int) -> DeviceAssignment | None:
    """Return the open (not yet closed) assignment of a device, if any."""
    return (
        db.query(DeviceAssignment)
        .filter(DeviceAssignment.device_id == device_id, DeviceAssignment.valid_to.is_(None))
        .first()
    )


def get_device_or_raise(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise DeviceNotFoundError("Dispositivo no encontrado")
    return device


def get_available_truck_or_raise(db: Session, truck_id: int) -> Truck:
    truck = db.get(Truck, truck_id)
    if truck is None:
        raise DeviceNotFoundError("Camión no encontrado")
    if not truck.active:
        raise DeviceError("El camión está inactivo")
    return truck


def provision_device(db: Session, identifier: str, truck_id: int) -> str:
    """Create a device, assign it to a truck and return its plaintext token."""
    identifier = identifier.strip()
    if not identifier:
        raise DeviceError("El identificador del dispositivo no puede estar vacío")
    if db.query(Device).filter(Device.identifier == identifier).first() is not None:
        raise DeviceError("Ya existe un dispositivo con ese identificador")
    truck = get_available_truck_or_raise(db, truck_id)
    open_on_truck = (
        db.query(DeviceAssignment)
        .filter(DeviceAssignment.truck_id == truck_id, DeviceAssignment.valid_to.is_(None))
        .first()
    )
    if open_on_truck is not None:
        raise DeviceError("El camión ya tiene un dispositivo asignado")

    token = generate_device_token()
    device = Device(
        identifier=identifier,
        token_hash=hash_device_token(token),
        organization_id=truck.organization_id,
    )
    db.add(device)
    db.flush()
    db.add(
        DeviceAssignment(
            device_id=device.id,
            truck_id=truck_id,
            valid_from=datetime.now(UTC),
        )
    )
    db.commit()
    return token


def reassign_device(db: Session, device_id: int, truck_id: int) -> DeviceAssignment:
    """Close the current open assignment and open a new one on another truck."""
    device = get_device_or_raise(db, device_id)
    if not device.active:
        raise DeviceError("El dispositivo está revocado")
    truck = get_available_truck_or_raise(db, truck_id)

    current = open_assignment_for(db, device.id)
    if current is not None and current.truck_id == truck.id:
        raise DeviceError("El dispositivo ya está asignado a ese camión")
    occupied = (
        db.query(DeviceAssignment)
        .filter(DeviceAssignment.truck_id == truck.id, DeviceAssignment.valid_to.is_(None))
        .first()
    )
    if occupied is not None:
        raise DeviceError("El camión ya tiene un dispositivo asignado")

    now = datetime.now(UTC)
    if current is not None:
        current.valid_to = now
        db.flush()
    assignment = DeviceAssignment(device_id=device.id, truck_id=truck.id, valid_from=now)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def rotate_device_token(db: Session, device_id: int) -> str:
    """Replace a device token, invalidating the previous one. Returns the new plaintext token."""
    device = get_device_or_raise(db, device_id)
    if not device.active:
        raise DeviceError("El dispositivo está revocado")
    token = generate_device_token()
    device.token_hash = hash_device_token(token)
    db.commit()
    return token


def revoke_device(db: Session, device_id: int) -> Device:
    """Deactivate a device and close its open assignment."""
    device = get_device_or_raise(db, device_id)
    device.active = False
    assignment = open_assignment_for(db, device.id)
    if assignment is not None:
        assignment.valid_to = datetime.now(UTC)
    db.commit()
    db.refresh(device)
    return device


def device_response(db: Session, device: Device) -> DeviceResponse:
    assignment = open_assignment_for(db, device.id)
    return DeviceResponse(
        id=device.id,
        identifier=device.identifier,
        active=device.active,
        organization_id=device.organization_id,
        assignment=(
            DeviceAssignmentInfo(truck_id=assignment.truck_id, valid_from=assignment.valid_from)
            if assignment is not None
            else None
        ),
    )


def _ensure_device_scope(current_user: User, device: Device) -> Device:
    """Hide devices outside the caller's organization instead of revealing them."""
    if current_user.role == ROLE_PLATFORM_ADMIN:
        return device
    if device.organization_id != current_user.organization_id:
        raise DeviceNotFoundError("Dispositivo no encontrado")
    return device


def _ensure_truck_scope(current_user: User, truck: Truck) -> Truck:
    """Hide trucks outside the caller's organization instead of revealing them."""
    if current_user.role == ROLE_PLATFORM_ADMIN:
        return truck
    if truck.organization_id != current_user.organization_id:
        raise DeviceNotFoundError("Camión no encontrado")
    return truck


def get_authenticated_device(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(device_bearer)],
    db: Session = Depends(get_db),
) -> Device:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")
    device = db.query(Device).filter(Device.token_hash == hash_device_token(credentials.credentials)).first()
    if device is None or not device.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")
    return device


def _raw_payload(point: object) -> str:
    try:
        return json.dumps(point, separators=(",", ":"), default=str)
    except (TypeError, ValueError):
        return json.dumps({"value": str(point)}, separators=(",", ":"))


def _assignment_for_point(db: Session, device_id: int, recorded_at: datetime) -> DeviceAssignment | None:
    return (
        db.query(DeviceAssignment)
        .filter(
            DeviceAssignment.device_id == device_id,
            DeviceAssignment.valid_from <= recorded_at,
            (DeviceAssignment.valid_to.is_(None) | (DeviceAssignment.valid_to > recorded_at)),
        )
        .first()
    )


def persist_ingest_alert(*, db: Session, device: Device, reason: str, raw_payload: str) -> None:
    """Alert seam: the current schema has no alert model, so rejection evidence is persisted here."""


@router.post("/ingest")
def ingest_device_batch(
    batch: DeviceIngestBatch,
    device: Device = Depends(get_authenticated_device),
    db: Session = Depends(get_db),
):
    results = []
    for raw_point in batch.points:
        sequence = raw_point.get("sequence") if isinstance(raw_point, dict) else None
        try:
            point = DeviceIngestPoint.model_validate(raw_point)
        except ValidationError:
            reason = "invalid_point"
            duplicate = db.query(RejectedIngestPoint).filter_by(
                device_id=device.id, batch_id=str(batch.batch_id), sequence=sequence
            ).first() if isinstance(sequence, int) else None
            if duplicate:
                results.append({"sequence": sequence, "status": "rejected", "reason": duplicate.reason, "replayed": True})
                continue
            rejected = RejectedIngestPoint(
                device_id=device.id,
                batch_id=str(batch.batch_id),
                sequence=sequence if isinstance(sequence, int) else None,
                reason=reason,
                raw_payload=_raw_payload(raw_point),
            )
            db.add(rejected)
            persist_ingest_alert(db=db, device=device, reason=reason, raw_payload=rejected.raw_payload)
            results.append({"sequence": sequence, "status": "rejected", "reason": reason})
            continue

        assignment = _assignment_for_point(db, device.id, point.recorded_at)
        truck = db.get(Truck, assignment.truck_id) if assignment else None
        if assignment is None:
            reason = "no_assignment"
        elif truck is None or not truck.active:
            reason = "inactive_truck" if truck is not None else "no_truck"
        else:
            existing = db.query(IngestedPoint).filter_by(
                assignment_id=assignment.id, batch_id=str(batch.batch_id), sequence=point.sequence
            ).first()
            if existing:
                results.append({"sequence": point.sequence, "status": "accepted", "replayed": True})
                continue
            try:
                with db.begin_nested():
                    db.add(IngestedPoint(
                        device_id=device.id, assignment_id=assignment.id, truck_id=truck.id,
                        batch_id=str(batch.batch_id), sequence=point.sequence, lat=point.lat,
                        long=point.long, speed=point.speed, heading=point.heading,
                        recorded_at=point.recorded_at,
                    ))
                    db.add(TrackingPoint(
                        truck_id=truck.id, lat=point.lat, long=point.long, speed=point.speed,
                        heading=point.heading, recorded_at=point.recorded_at,
                    ))
                    db.flush()
                results.append({"sequence": point.sequence, "status": "accepted", "replayed": False})
                continue
            except IntegrityError:
                # A concurrent retry wins the unique constraint; report it as replayed.
                results.append({"sequence": point.sequence, "status": "accepted", "replayed": True})
                continue

        raw = _raw_payload(raw_point)
        duplicate = db.query(RejectedIngestPoint).filter_by(
            device_id=device.id, batch_id=str(batch.batch_id), sequence=sequence
        ).first() if isinstance(sequence, int) else None
        if duplicate:
            results.append({"sequence": sequence, "status": "rejected", "reason": duplicate.reason, "replayed": True})
            continue
        db.add(RejectedIngestPoint(
            device_id=device.id, assignment_id=assignment.id if assignment else None,
            batch_id=str(batch.batch_id), sequence=sequence if isinstance(sequence, int) else None,
            reason=reason, raw_payload=raw,
        ))
        persist_ingest_alert(db=db, device=device, reason=reason, raw_payload=raw)
        results.append({"sequence": sequence, "status": "rejected", "reason": reason, "replayed": False})

    db.commit()
    return {"batch_id": str(batch.batch_id), "results": results}


# ---- Administrative device lifecycle ----


@router.get("", response_model=list[DeviceResponse])
def list_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_platform),
):
    query = db.query(Device).order_by(Device.id)
    if current_user.role != ROLE_PLATFORM_ADMIN:
        query = query.filter(Device.organization_id == current_user.organization_id)
    return [device_response(db, device) for device in query.all()]


@router.post("", response_model=DeviceProvisioned, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_platform),
):
    truck = db.get(Truck, payload.truck_id)
    if truck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camión no encontrado"
        )
    if (
        current_user.role != ROLE_PLATFORM_ADMIN
        and truck.organization_id != current_user.organization_id
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Camión no encontrado"
        )
    try:
        token = provision_device(db, payload.identifier, payload.truck_id)
    except DeviceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    device = db.query(Device).filter(Device.identifier == payload.identifier).one()
    return DeviceProvisioned(**device_response(db, device).model_dump(), token=token)


@router.post("/{device_id}/reassign", response_model=DeviceResponse)
def reassign(
    device_id: int,
    payload: DeviceReassign,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    try:
        device = _ensure_device_scope(current_user, get_device_or_raise(db, device_id))
        truck = db.get(Truck, payload.truck_id)
        if truck is not None:
            _ensure_truck_scope(current_user, truck)
        reassign_device(db, device.id, payload.truck_id)
    except DeviceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return device_response(db, get_device_or_raise(db, device_id))


@router.post("/{device_id}/token/rotate", response_model=DeviceProvisioned)
def rotate_token(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    try:
        device = _ensure_device_scope(current_user, get_device_or_raise(db, device_id))
        token = rotate_device_token(db, device.id)
    except DeviceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return DeviceProvisioned(
        **device_response(db, get_device_or_raise(db, device_id)).model_dump(), token=token
    )


@router.post("/{device_id}/revoke", response_model=DeviceResponse)
def revoke(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin),
):
    try:
        device = _ensure_device_scope(current_user, get_device_or_raise(db, device_id))
        device = revoke_device(db, device.id)
    except DeviceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return device_response(db, device)
