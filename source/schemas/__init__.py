"""Pydantic request/response schemas."""

from .auth import Token, UserCreate, UserResponse
from .destination import (
    ChargerCreate,
    ChargerResponse,
    DepotCreate,
    DepotResponse,
    StopCoordinates,
    StopCreate,
    StopResponse,
    TripCreate,
    TripResponse,
    TripRouteResponse,
)
from .device import (
    DeviceAssignmentInfo,
    DeviceCreate,
    DeviceProvisioned,
    DeviceReassign,
    DeviceResponse,
)
from .ingestion import DeviceIngestBatch, DeviceIngestPoint
from .organization import InvitationRotate, OrganizationCreate, OrganizationResponse
from .truck import Truck

__all__ = [
    "ChargerCreate",
    "ChargerResponse",
    "DepotCreate",
    "DepotResponse",
    "DeviceAssignmentInfo",
    "DeviceCreate",
    "DeviceIngestBatch",
    "DeviceIngestPoint",
    "DeviceProvisioned",
    "DeviceReassign",
    "DeviceResponse",
    "InvitationRotate",
    "OrganizationCreate",
    "OrganizationResponse",
    "StopCoordinates",
    "StopCreate",
    "StopResponse",
    "Token",
    "TripCreate",
    "TripResponse",
    "TripRouteResponse",
    "Truck",
    "UserCreate",
    "UserResponse",
]
