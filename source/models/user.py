from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

if TYPE_CHECKING:
    from source.models.organization import Organization


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped [str] = mapped_column()
    hashed_password: Mapped [str] = mapped_column()
    disabled: Mapped[bool] = mapped_column(default=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="cliente", server_default="cliente")
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization"] = relationship(back_populates="users")

