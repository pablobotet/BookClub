"""Application services implementing reading-club domain operations."""

from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.models import Membership, ReadingGroup, User
from reading_club.repositories import (
    GroupRepository,
    MembershipRepository,
    UserRepository,
)
from reading_club.schemas import (
    GroupCreate,
    GroupUpdate,
    MembershipCreate,
    UserCreate,
    UserUpdate,
)

Model = TypeVar("Model", User, ReadingGroup, Membership)


class ReadingClubService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.groups = GroupRepository(session)
        self.memberships = MembershipRepository(session)

    async def create_user(self, data: UserCreate) -> User:
        if await self.users.get_by_email(data.email):
            self._conflict("A user with this email already exists")
        user = User(**data.model_dump())
        self.session.add(user)
        return await self._save(user)

    async def list_users(self) -> list[User]:
        return await self.users.list()

    async def get_user(self, user_id: UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            self._not_found("User")
        return user  # type: ignore[return-value]

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self.get_user(user_id)
        changes = data.model_dump(exclude_unset=True)
        email = changes.get("email")
        if email is not None:
            existing = await self.users.get_by_email(email)
            if existing is not None and existing.id != user.id:
                self._conflict("A user with this email already exists")
        for field, value in changes.items():
            setattr(user, field, value)
        return await self._save(user)

    async def create_group(self, data: GroupCreate) -> ReadingGroup:
        if await self.groups.get_by_name(data.name):
            self._conflict("A group with this name already exists")
        group = ReadingGroup(**data.model_dump())
        self.session.add(group)
        return await self._save(group)

    async def list_groups(self) -> list[ReadingGroup]:
        return await self.groups.list()

    async def get_group(self, group_id: UUID) -> ReadingGroup:
        group = await self.groups.get(group_id)
        if group is None:
            self._not_found("Group")
        return group  # type: ignore[return-value]

    async def update_group(self, group_id: UUID, data: GroupUpdate) -> ReadingGroup:
        group = await self.get_group(group_id)
        changes = data.model_dump(exclude_unset=True)
        name = changes.get("name")
        if name is not None:
            existing = await self.groups.get_by_name(name)
            if existing is not None and existing.id != group.id:
                self._conflict("A group with this name already exists")
        for field, value in changes.items():
            setattr(group, field, value)
        return await self._save(group)

    async def add_member(self, group_id: UUID, data: MembershipCreate) -> Membership:
        await self.get_group(group_id)
        await self.get_user(data.user_id)
        if await self.memberships.get(group_id, data.user_id):
            self._conflict("User is already a member of this group")
        membership = Membership(group_id=group_id, **data.model_dump())
        self.session.add(membership)
        return await self._save(membership)

    async def list_members(self, group_id: UUID) -> list[Membership]:
        await self.get_group(group_id)
        return await self.memberships.list_for_group(group_id)

    async def remove_member(self, group_id: UUID, user_id: UUID) -> None:
        await self.get_group(group_id)
        membership = await self.memberships.get(group_id, user_id)
        if membership is None:
            self._not_found("Membership")
        await self.session.delete(membership)
        await self._commit()

    async def _save(self, instance: Model) -> Model:
        await self._commit()
        await self.session.refresh(instance)
        return instance

    async def _commit(self) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The requested change conflicts with existing data",
            ) from error

    @staticmethod
    def _not_found(resource: str) -> None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found"
        )

    @staticmethod
    def _conflict(detail: str) -> None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
