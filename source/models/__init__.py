"""ORM models.

Importing this package registers every table on `Base.metadata`, which is what
Alembic autogeneration and `Base.metadata.create_all` rely on.
"""

from .device import Device, DeviceAssignment
from .ingestion import IngestedPoint, RejectedIngestPoint
from .organization import Organization
from .truck import TrackingPoint, Truck
from .user import User

__all__ = [
    "Device",
    "DeviceAssignment",
    "IngestedPoint",
    "Organization",
    "RejectedIngestPoint",
    "TrackingPoint",
    "Truck",
    "User",
]
