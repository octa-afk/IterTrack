from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

if TYPE_CHECKING:
    from source.models.truck import Truck
    from source.models.user import User


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    invitation_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    # An invitation stays valid while it is neither revoked nor expired.
    # Null means "no expiry" and keeps organizations created before this
    # feature usable.
    invitation_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    invitation_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    users: Mapped[list["User"]] = relationship(back_populates="organization")
    trucks: Mapped[list["Truck"]] = relationship(back_populates="organization")

    @property
    def invitation_active(self) -> bool:
        """Whether the current invitation code can still be used to register."""
        if self.invitation_revoked_at is not None:
            return False
        if self.invitation_expires_at is None:
            return True
        expires_at = self.invitation_expires_at
        # SQLite does not preserve timezones, so a value read back from it can
        # be naive even though the column is timezone-aware.
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at > datetime.now(UTC)
