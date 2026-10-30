from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

if TYPE_CHECKING:
    from source.models.organization import Organization


class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(unique=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    organization: Mapped["Organization"] = relationship(back_populates="trucks")

    tracking_points: Mapped[list["TrackingPoint"]] = relationship(back_populates="truck")

class TrackingPoint(Base):
    __tablename__ = "tracking_points"
    __table_args__ = (
        Index("ix_tracking_points_truck_recorded_at_id", "truck_id", text("recorded_at DESC"), text("id DESC")),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"))
    lat: Mapped[float]
    lng: Mapped[float]
    speed: Mapped[float]
    heading: Mapped[float]
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)
    # recorded_at: momento en que se midió la ubicación (lo informa el dispositivo cuando exista).
    # received_at: momento en que el servidor recibió el punto. Son tiempos distintos: un punto
    # almacenado sin conexión puede llegar mucho después de medirse.
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    truck: Mapped["Truck"] = relationship(back_populates="tracking_points")
