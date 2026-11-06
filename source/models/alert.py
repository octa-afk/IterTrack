from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

if TYPE_CHECKING:
    from source.models.device import Device
    from source.models.ingestion import RejectedIngestPoint
    from source.models.organization import Organization


class Alert(Base):
    """Rechazos de ingesta agrupados mientras la alerta está abierta.

    La clave de agrupación es (dispositivo, tipo de problema): un equipo mal
    aprovisionado rechaza en cada batch, y una alerta con veinte ocurrencias dice
    más que veinte alertas sueltas. Si se cierra y el problema vuelve, la nueva
    se enlaza con `previous_alert_id`, así se distingue una recurrencia de un
    problema nuevo.
    """

    __tablename__ = "alerts"
    __table_args__ = (
        CheckConstraint("status IN ('open','closed')", name="ck_alerts_status"),
        # La búsqueda de "la alerta abierta de este equipo y este problema" corre
        # en cada punto rechazado.
        Index("ix_alerts_open_lookup", "device_id", "problem_type", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    # Se copia del equipo al crear la alerta: una alerta vieja tiene que seguir
    # siendo legible aunque el dispositivo cambie de organización después.
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    problem_type: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(
        String(16), default="open", server_default=text("'open'")
    )
    previous_alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("alerts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latest_occurrence_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    device: Mapped["Device"] = relationship()
    organization: Mapped["Organization"] = relationship()
    occurrences: Mapped[list["AlertOccurrence"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan"
    )


class AlertOccurrence(Base):
    """Evidencia: qué punto rechazado generó esta ocurrencia."""

    __tablename__ = "alert_occurrences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"), index=True)
    rejected_point_id: Mapped[int] = mapped_column(
        ForeignKey("rejected_ingest_points.id")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    alert: Mapped["Alert"] = relationship(back_populates="occurrences")
    rejected_point: Mapped["RejectedIngestPoint"] = relationship()
