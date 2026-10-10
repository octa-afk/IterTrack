from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

class Truck(Base):
    __tablename__ = "trucks"

    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(unique=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization"] = relationship(back_populates="trucks")

    tracking_points: Mapped[list["TrackingPoint"]] = relationship(back_populates="truck")

class TrackingPoint(Base):
    __tablename__ = "tracking_points"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    truck_id: Mapped[int] = mapped_column(ForeignKey("trucks.id"))
    lat: Mapped[float]
    long: Mapped[float]
    timestamp: Mapped[datetime] = mapped_column(default=datetime.now)

    truck: Mapped["Truck"] = relationship(back_populates="tracking_points")
