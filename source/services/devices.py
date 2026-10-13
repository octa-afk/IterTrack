import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from source.models.device import Device, DeviceAssignment
from source.models.truck import Truck


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
            valid_from=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return token
