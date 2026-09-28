"""Database models for reading-club profiles and groups."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from reading_club.db import Base


class MembershipRole(str, enum.Enum):
    """Roles available to a reading-group member."""

    MEMBER = "member"
    ADMIN = "admin"


class TimestampedModel:
    """Columns shared by records that track their lifecycle."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampedModel, Base):
    """A managed reading-club profile."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    memberships: Mapped[list[Membership]] = relationship(back_populates="user")


class ReadingGroup(TimestampedModel, Base):
    """A named reading group."""

    __tablename__ = "reading_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    memberships: Mapped[list[Membership]] = relationship(back_populates="group")


class Membership(Base):
    """Associates a user with a reading group and role."""

    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_memberships_user_group"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[MembershipRole] = mapped_column(
        Enum(
            MembershipRole,
            name="membership_role",
            native_enum=True,
            values_callable=lambda roles: [role.value for role in roles],
        ),
        nullable=False,
        default=MembershipRole.MEMBER,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user: Mapped[User] = relationship(back_populates="memberships")
    group: Mapped[ReadingGroup] = relationship(back_populates="memberships")
