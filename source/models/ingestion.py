from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from source.database.database import Base


class IngestedPoint(Base):
    __tablename__ = "ingested_points"
    __table_args__ = (
        UniqueConstraint("assignment_id", "batch_id", "sequence", name="uq_ingested_assignment_batch_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    assignment_id: Mapped[int] = mapped_column(ForeignKey("device_assignments.id"))
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"))
    batch_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int] = mapped_column(Integer)
    lat: Mapped[float]
    long: Mapped[float]
    speed: Mapped[float]
    heading: Mapped[float]
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class RejectedIngestPoint(Base):
    __tablename__ = "rejected_ingest_points"
    __table_args__ = (
        UniqueConstraint("device_id", "batch_id", "sequence", name="uq_rejected_device_batch_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("device_assignments.id"), nullable=True
    )
    batch_id: Mapped[str] = mapped_column(String(36))
    sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reason: Mapped[str] = mapped_column(String(120))
    raw_payload: Mapped[str] = mapped_column(Text)
    rejected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
