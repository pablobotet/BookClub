"""Async persistence operations for reading-club domain models."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.models import Membership, ReadingGroup, User


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
