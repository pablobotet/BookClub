"""Database models for reading-club profiles and groups."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
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
    reviews: Mapped[list[Review]] = relationship(back_populates="user")
    votes: Mapped[list[Vote]] = relationship(back_populates="user")
    requested_selections: Mapped[list[Selection]] = relationship(
        back_populates="requested_by"
    )


class ReadingGroup(TimestampedModel, Base):
    """A named reading group."""

    __tablename__ = "reading_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    memberships: Mapped[list[Membership]] = relationship(back_populates="group")
    reviews: Mapped[list[Review]] = relationship(back_populates="group")
    votes: Mapped[list[Vote]] = relationship(back_populates="group")
    selections: Mapped[list[Selection]] = relationship(back_populates="group")


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


class Book(TimestampedModel, Base):
    """A global catalog record for a book."""

    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    isbn: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True)
    publication_year: Mapped[int | None] = mapped_column(nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviews: Mapped[list[Review]] = relationship(back_populates="book")
    votes: Mapped[list[Vote]] = relationship(back_populates="book")
    selections: Mapped[list[Selection]] = relationship(back_populates="book")


class Review(TimestampedModel, Base):
    """A member's rating and optional review of a book in a group."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_reviews_rating_range"),
        UniqueConstraint(
            "user_id", "group_id", "book_id", name="uq_reviews_user_group_book"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(nullable=False)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    group: Mapped[ReadingGroup] = relationship(back_populates="reviews")
    book: Mapped[Book] = relationship(back_populates="reviews")
    user: Mapped[User] = relationship(back_populates="reviews")


class Vote(Base):
    """A member's vote for a candidate next book in a group."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "group_id", "book_id", name="uq_votes_user_group_book"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    group: Mapped[ReadingGroup] = relationship(back_populates="votes")
    book: Mapped[Book] = relationship(back_populates="votes")
    user: Mapped[User] = relationship(back_populates="votes")


class Selection(Base):
    """An immutable record of a group's random next-book draw."""

    __tablename__ = "selections"
    __table_args__ = (
        CheckConstraint("candidate_count > 0", name="ck_selections_candidate_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reading_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("books.id"), nullable=False, index=True
    )
    requested_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    candidate_count: Mapped[int] = mapped_column(nullable=False)
    candidate_book_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    group: Mapped[ReadingGroup] = relationship(back_populates="selections")
    book: Mapped[Book] = relationship(back_populates="selections")
    requested_by: Mapped[User] = relationship(back_populates="requested_selections")
