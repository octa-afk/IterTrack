from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from source.database.database import Base

if TYPE_CHECKING:
    from source.models.organization import Organization

# Two orthogonal concerns are encoded in one explicit enum so no endpoint has to
# guess the scope of a bare "admin":
#   platform_admin -> the whole platform (IterTrack staff)
#   org_admin      -> a single organization (the customer's administrator)
#   member         -> read-only member of a single organization
ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_ORG_ADMIN = "org_admin"
ROLE_MEMBER = "member"
ROLE_VALUES = (ROLE_PLATFORM_ADMIN, ROLE_ORG_ADMIN, ROLE_MEMBER)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('platform_admin', 'org_admin', 'member')",
            name="ck_users_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True)
    full_name: Mapped [str] = mapped_column()
    hashed_password: Mapped [str] = mapped_column()
    disabled: Mapped[bool] = mapped_column(default=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ROLE_MEMBER, server_default=ROLE_MEMBER
    )
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization"] = relationship(back_populates="users")
