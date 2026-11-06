from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

"""
Destinos tercerizados: el dador de carga entrega una lista de direcciones, la
flota asigna un camión y nosotros resolvemos dirección -> coordenada.

La coordenada es la fuente de verdad; la dirección es texto para mostrar. Por
eso `AddressCache` guarda la resolución por dirección normalizada: la segunda
importación de la misma dirección no vuelve a consultar al proveedor.
"""

TRIP_STATUSES = ("planned", "in_progress", "done", "cancelled")
STOP_STATUSES = ("pending", "arrived", "delivered", "failed")


class Charger(Base):
    """Dador de carga: la empresa que terceriza el envío (ej. una de colchones).

    No es un inquilino: no tiene login ni invitaciones. Es una dimensión de la
    organización que opera la flota.
    """

    __tablename__ = "chargers"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_chargers_org_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(120), nullable=True)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    trips: Mapped[list["Trip"]] = relationship(back_populates="charger")


class Depot(Base):
    """Depósito de donde salen los camiones.

    Guarda la ubicación desde el arranque aunque la elegibilidad todavía no la
    use: el chequeo de radio ("está en el depósito") es el paso siguiente y sin
    lat/lng habría que migrar de nuevo.
    """

    __tablename__ = "depots"
    __table_args__ = (
        UniqueConstraint("organization_id", "name", name="uq_depots_org_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    radius_m: Mapped[int] = mapped_column(default=150, server_default=text("150"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Trip(Base):
    """Un envío con fecha. El chofer vive acá, no en el camión: en
    tercerización el mismo camión rota de chofer según el viaje."""

    __tablename__ = "trips"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "external_ref", name="uq_trips_org_external_ref"
        ),
        CheckConstraint(
            "status IN ('planned','in_progress','done','cancelled')",
            name="ck_trips_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    charger_id: Mapped[int] = mapped_column(ForeignKey("chargers.id"), index=True)
    truck_id: Mapped[int | None] = mapped_column(
        ForeignKey("trucks.id"), nullable=True, index=True
    )
    driver_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Fecha y hora de salida: "salir a las 07:30" no entra en un `date`.
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    depot_id: Mapped[int | None] = mapped_column(
        ForeignKey("depots.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="planned")
    # Idempotencia: el cliente reenvía lo que le mandaron y un mismo envío no
    # puede entrar dos veces. NULL se repite sin conflicto.
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    charger: Mapped["Charger"] = relationship(back_populates="trips")
    stops: Mapped[list["TripStop"]] = relationship(
        back_populates="trip",
        order_by="TripStop.seq",
        cascade="all, delete-orphan",
    )


class TripStop(Base):
    """Un destino del viaje, con su coordenada y su procedencia."""

    __tablename__ = "trip_stops"
    __table_args__ = (
        UniqueConstraint("trip_id", "seq", name="uq_trip_stops_trip_seq"),
        CheckConstraint(
            "status IN ('pending','arrived','delivered','failed')",
            name="ck_trip_stops_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("trips.id"), index=True)
    seq: Mapped[int]
    address: Mapped[str] = mapped_column(String(300))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # De dónde salió la coordenada: cache | provided | nominatim | manual.
    geo_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    geo_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    receiver: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    departed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    trip: Mapped["Trip"] = relationship(back_populates="stops")


class AddressCache(Base):
    """Dirección normalizada -> coordenada, una vez por organización.

    Sin esta tabla cada importación volvería a geocodificar las mismas
    direcciones: el dador entrega a los mismos comercios todas las semanas.
    """

    __tablename__ = "address_cache"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "address_norm", name="uq_address_cache_org_norm"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    address_norm: Mapped[str] = mapped_column(String(300))
    address_raw: Mapped[str] = mapped_column(String(300))
    lat: Mapped[float]
    lng: Mapped[float]
    provider: Mapped[str] = mapped_column(String(24))
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
