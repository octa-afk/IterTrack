"""ORM models.

Importing this package registers every table on `Base.metadata`, which is what
Alembic autogeneration and `Base.metadata.create_all` rely on.
"""

from .destination import AddressCache, Charger, Trip, TripStop
from .device import Device, DeviceAssignment
from .ingestion import IngestedPoint, RejectedIngestPoint
from .organization import Organization
from .truck import TrackingPoint, Truck
from .user import User

__all__ = [
    "AddressCache",
    "Charger",
    "Device",
    "DeviceAssignment",
    "IngestedPoint",
    "Organization",
    "RejectedIngestPoint",
    "TrackingPoint",
    "Trip",
    "TripStop",
    "Truck",
    "User",
]
