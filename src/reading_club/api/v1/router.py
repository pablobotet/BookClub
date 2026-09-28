"""Version 1 API router."""

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.db import get_db_session
from reading_club.schemas import (
    BookCreate,
    BookResponse,
    BookUpdate,
    GroupCreate,
    GroupResponse,
    GroupUpdate,
    MembershipCreate,
    MembershipResponse,
    ReviewCreate,
    ReviewResponse,
    ReviewUpdate,
    SelectionCreate,
    SelectionResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
    VoteCreate,
    VoteResponse,
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


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    data: BookCreate, service: ReadingClubService = Depends(get_service)
) -> BookResponse:
    return BookResponse.model_validate(await service.create_book(data))


@router.get("/books", response_model=list[BookResponse])
async def list_books(
    service: ReadingClubService = Depends(get_service),
) -> list[BookResponse]:
    return [BookResponse.model_validate(book) for book in await service.list_books()]


@router.get("/books/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: UUID, service: ReadingClubService = Depends(get_service)
) -> BookResponse:
    return BookResponse.model_validate(await service.get_book(book_id))


@router.patch("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: UUID, data: BookUpdate, service: ReadingClubService = Depends(get_service)
) -> BookResponse:
    return BookResponse.model_validate(await service.update_book(book_id, data))


@router.post(
    "/groups/{group_id}/reviews",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review(
    group_id: UUID,
    data: ReviewCreate,
    service: ReadingClubService = Depends(get_service),
) -> ReviewResponse:
    return ReviewResponse.model_validate(await service.create_review(group_id, data))


@router.get("/groups/{group_id}/reviews", response_model=list[ReviewResponse])
async def list_reviews(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> list[ReviewResponse]:
    return [
        ReviewResponse.model_validate(review)
        for review in await service.list_reviews(group_id)
    ]


@router.get("/groups/{group_id}/reviews/{review_id}", response_model=ReviewResponse)
async def get_review(
    group_id: UUID, review_id: UUID, service: ReadingClubService = Depends(get_service)
) -> ReviewResponse:
    return ReviewResponse.model_validate(await service.get_review(group_id, review_id))


@router.patch("/groups/{group_id}/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    group_id: UUID,
    review_id: UUID,
    data: ReviewUpdate,
    service: ReadingClubService = Depends(get_service),
) -> ReviewResponse:
    return ReviewResponse.model_validate(
        await service.update_review(group_id, review_id, data)
    )


@router.post(
    "/groups/{group_id}/votes",
    response_model=VoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_vote(
    group_id: UUID, data: VoteCreate, service: ReadingClubService = Depends(get_service)
) -> VoteResponse:
    return VoteResponse.model_validate(await service.create_vote(group_id, data))


@router.get("/groups/{group_id}/votes", response_model=list[VoteResponse])
async def list_votes(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> list[VoteResponse]:
    return [
        VoteResponse.model_validate(vote) for vote in await service.list_votes(group_id)
    ]


@router.delete(
    "/groups/{group_id}/votes/{vote_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_vote(
    group_id: UUID, vote_id: UUID, service: ReadingClubService = Depends(get_service)
) -> Response:
    await service.remove_vote(group_id, vote_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/groups/{group_id}/selections",
    response_model=SelectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_selection(
    group_id: UUID,
    data: SelectionCreate,
    service: ReadingClubService = Depends(get_service),
) -> SelectionResponse:
    return SelectionResponse.model_validate(
        await service.create_selection(group_id, data)
    )


@router.get("/groups/{group_id}/selections", response_model=list[SelectionResponse])
async def list_selections(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> list[SelectionResponse]:
    return [
        SelectionResponse.model_validate(selection)
        for selection in await service.list_selections(group_id)
    ]


@router.get(
    "/groups/{group_id}/selections/latest", response_model=SelectionResponse
)
async def get_latest_selection(
    group_id: UUID, service: ReadingClubService = Depends(get_service)
) -> SelectionResponse:
    return SelectionResponse.model_validate(
        await service.get_latest_selection(group_id)
    )
