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
from source.schemas.ingestion import DeviceIngestBatch, DeviceIngestPoint

router = APIRouter(prefix="/devices", tags=["devices"])
device_bearer = HTTPBearer(auto_error=False)


def generate_device_token() -> str:
    """Return a new random device token (shown once, never stored in plaintext)."""
    return secrets.token_urlsafe(32)


def hash_device_token(token: str) -> str:
    """Hash a device token with SHA-256. Tokens are high-entropy, so no bcrypt is needed."""
    return hashlib.sha256(token.encode()).hexdigest()


def provision_device(db: Session, identifier: str, truck_id: int) -> str:
    """Create a device, assign it to a truck and return its plaintext token."""
    identifier = identifier.strip()
    if not identifier:
        raise ValueError("Device identifier must not be empty")
    if db.query(Device).filter(Device.identifier == identifier).first() is not None:
        raise ValueError(f"Device '{identifier}' already exists")
    if db.get(Truck, truck_id) is None:
        raise ValueError(f"Truck {truck_id} does not exist")
    open_on_truck = (
        db.query(DeviceAssignment)
        .filter(DeviceAssignment.truck_id == truck_id, DeviceAssignment.valid_to.is_(None))
        .first()
    )
    if open_on_truck is not None:
        raise ValueError(f"Truck {truck_id} already has an open device assignment")

    token = generate_device_token()
    device = Device(identifier=identifier, token_hash=hash_device_token(token))
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
