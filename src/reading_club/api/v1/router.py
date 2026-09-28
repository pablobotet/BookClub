"""Version 1 API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.db import get_db_session
from reading_club.schemas import (
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    MembershipCreate,
    MembershipResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from reading_club.services import ReadingClubService

router = APIRouter()


def get_service(
    session: AsyncSession = Depends(get_db_session),
) -> ReadingClubService:
    """Create the service for a request's database session."""
    return ReadingClubService(session)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate, service: ReadingClubService = Depends(get_service)
) -> UserResponse:
    return UserResponse.model_validate(await service.create_user(data))


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    service: ReadingClubService = Depends(get_service),
) -> list[UserResponse]:
    return [UserResponse.model_validate(user) for user in await service.list_users()]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID, service: ReadingClubService = Depends(get_service)
) -> UserResponse:
    return UserResponse.model_validate(await service.get_user(user_id))


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID, data: UserUpdate, service: ReadingClubService = Depends(get_service)
) -> UserResponse:
    return UserResponse.model_validate(await service.update_user(user_id, data))


@router.post(
    "/groups", response_model=GroupResponse, status_code=status.HTTP_201_CREATED
)
async def create_group(
    data: GroupCreate, service: ReadingClubService = Depends(get_service)
) -> GroupResponse:
    return GroupResponse.model_validate(await service.create_group(data))


@router.get("/groups", response_model=list[GroupResponse])
async def list_groups(
    service: ReadingClubService = Depends(get_service),
) -> list[GroupResponse]:
    return [
        GroupResponse.model_validate(group) for group in await service.list_groups()
    ]


@router.get("/groups/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> GroupResponse:
    return GroupResponse.model_validate(await service.get_group(group_id))


@router.patch("/groups/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    data: GroupUpdate,
    service: ReadingClubService = Depends(get_service),
) -> GroupResponse:
    return GroupResponse.model_validate(await service.update_group(group_id, data))


@router.post(
    "/groups/{group_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    group_id: UUID,
    data: MembershipCreate,
    service: ReadingClubService = Depends(get_service),
) -> MembershipResponse:
    return MembershipResponse.model_validate(await service.add_member(group_id, data))


@router.get("/groups/{group_id}/members", response_model=list[MembershipResponse])
async def list_members(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> list[MembershipResponse]:
    return [
        MembershipResponse.model_validate(membership)
        for membership in await service.list_members(group_id)
    ]


@router.delete(
    "/groups/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    group_id: UUID, user_id: UUID, service: ReadingClubService = Depends(get_service)
) -> Response:
    await service.remove_member(group_id, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
