"""Async persistence operations for reading-club domain models."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.models import (
    Book,
    Membership,
    ReadingGroup,
    Review,
    Selection,
    User,
    Vote,
)


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))

    async def list(self) -> list[User]:
        return list(
            (await self.session.scalars(select(User).order_by(User.created_at))).all()
        )


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, group_id: UUID) -> ReadingGroup | None:
        return await self.session.get(ReadingGroup, group_id)

    async def get_by_name(self, name: str) -> ReadingGroup | None:
        return await self.session.scalar(
            select(ReadingGroup).where(ReadingGroup.name == name)
        )

    async def list(self) -> list[ReadingGroup]:
        return list(
            (
                await self.session.scalars(
                    select(ReadingGroup).order_by(ReadingGroup.created_at)
                )
            ).all()
        )


class MembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, group_id: UUID, user_id: UUID) -> Membership | None:
        return await self.session.scalar(
            select(Membership).where(
                Membership.group_id == group_id, Membership.user_id == user_id
            )
        )

    async def list_for_group(self, group_id: UUID) -> list[Membership]:
        return list(
            (
                await self.session.scalars(
                    select(Membership)
                    .where(Membership.group_id == group_id)
                    .order_by(Membership.joined_at)
                )
            ).all()
        )


class BookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, book_id: UUID) -> Book | None:
        return await self.session.get(Book, book_id)

    async def get_by_isbn(self, isbn: str) -> Book | None:
        return await self.session.scalar(select(Book).where(Book.isbn == isbn))

    async def list(self) -> list[Book]:
        return list(
            (await self.session.scalars(select(Book).order_by(Book.created_at))).all()
        )


class ReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, review_id: UUID) -> Review | None:
        return await self.session.get(Review, review_id)

    async def get_for_user_book(
        self, group_id: UUID, user_id: UUID, book_id: UUID
    ) -> Review | None:
        return await self.session.scalar(
            select(Review).where(
                Review.group_id == group_id,
                Review.user_id == user_id,
                Review.book_id == book_id,
            )
        )

    async def list_for_group(self, group_id: UUID) -> list[Review]:
        return list(
            (
                await self.session.scalars(
                    select(Review)
                    .where(Review.group_id == group_id)
                    .order_by(Review.created_at)
                )
            ).all()
        )


class VoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, vote_id: UUID) -> Vote | None:
        return await self.session.get(Vote, vote_id)

    async def get_for_user_book(
        self, group_id: UUID, user_id: UUID, book_id: UUID
    ) -> Vote | None:
        return await self.session.scalar(
            select(Vote).where(
                Vote.group_id == group_id,
                Vote.user_id == user_id,
                Vote.book_id == book_id,
            )
        )

    async def list_for_group(self, group_id: UUID) -> list[Vote]:
        return list(
            (
                await self.session.scalars(
                    select(Vote)
                    .where(Vote.group_id == group_id)
                    .order_by(Vote.created_at)
                )
            ).all()
        )

    async def list_candidate_book_ids(self, group_id: UUID) -> list[UUID]:
        return list(
            (
                await self.session.scalars(
                    select(Vote.book_id)
                    .where(Vote.group_id == group_id)
                    .distinct()
                    .order_by(Vote.book_id)
                )
            ).all()
        )


class SelectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_group(self, group_id: UUID) -> list[Selection]:
        return list(
            (
                await self.session.scalars(
                    select(Selection)
                    .where(Selection.group_id == group_id)
                    .order_by(Selection.created_at.desc(), Selection.id.desc())
                )
            ).all()
        )

    async def latest_for_group(self, group_id: UUID) -> Selection | None:
        return await self.session.scalar(
            select(Selection)
            .where(Selection.group_id == group_id)
            .order_by(Selection.created_at.desc(), Selection.id.desc())
            .limit(1)
        )
