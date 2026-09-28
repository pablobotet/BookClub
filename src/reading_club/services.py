"""Application services implementing reading-club domain operations."""

import secrets
from collections.abc import Callable, Sequence
from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from reading_club.models import (
    Book,
    Membership,
    MembershipRole,
    ReadingGroup,
    Review,
    Selection,
    User,
    Vote,
)
from reading_club.repositories import (
    BookRepository,
    GroupRepository,
    MembershipRepository,
    ReviewRepository,
    SelectionRepository,
    UserRepository,
    VoteRepository,
)
from reading_club.schemas import (
    BookCreate,
    BookUpdate,
    GroupCreate,
    GroupUpdate,
    MembershipCreate,
    ReviewCreate,
    ReviewUpdate,
    SelectionCreate,
    UserCreate,
    UserUpdate,
    VoteCreate,
)

Model = TypeVar("Model", User, ReadingGroup, Membership, Book, Review, Vote, Selection)
SelectionStrategy = Callable[[Sequence[UUID]], UUID]


class ReadingClubService:
    def __init__(
        self,
        session: AsyncSession,
        selection_strategy: SelectionStrategy = secrets.choice,
    ) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.groups = GroupRepository(session)
        self.memberships = MembershipRepository(session)
        self.books = BookRepository(session)
        self.reviews = ReviewRepository(session)
        self.votes = VoteRepository(session)
        self.selections = SelectionRepository(session)
        self.selection_strategy = selection_strategy

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

    async def create_book(self, data: BookCreate) -> Book:
        if data.isbn is not None and await self.books.get_by_isbn(data.isbn):
            self._conflict("A book with this ISBN already exists")
        book = Book(**data.model_dump())
        self.session.add(book)
        return await self._save(book)

    async def list_books(self) -> list[Book]:
        return await self.books.list()

    async def get_book(self, book_id: UUID) -> Book:
        book = await self.books.get(book_id)
        if book is None:
            self._not_found("Book")
        return book  # type: ignore[return-value]

    async def update_book(self, book_id: UUID, data: BookUpdate) -> Book:
        book = await self.get_book(book_id)
        changes = data.model_dump(exclude_unset=True)
        isbn = changes.get("isbn")
        if isbn is not None:
            existing = await self.books.get_by_isbn(isbn)
            if existing is not None and existing.id != book.id:
                self._conflict("A book with this ISBN already exists")
        for field, value in changes.items():
            setattr(book, field, value)
        return await self._save(book)

    async def create_review(self, group_id: UUID, data: ReviewCreate) -> Review:
        await self.get_group(group_id)
        await self.get_book(data.book_id)
        await self._require_active_member(group_id, data.user_id)
        if await self.reviews.get_for_user_book(group_id, data.user_id, data.book_id):
            self._conflict("User has already reviewed this book in this group")
        review = Review(group_id=group_id, **data.model_dump())
        self.session.add(review)
        return await self._save(review)

    async def list_reviews(self, group_id: UUID) -> list[Review]:
        await self.get_group(group_id)
        return await self.reviews.list_for_group(group_id)

    async def get_review(self, group_id: UUID, review_id: UUID) -> Review:
        await self.get_group(group_id)
        review = await self.reviews.get(review_id)
        if review is None or review.group_id != group_id:
            self._not_found("Review")
        return review  # type: ignore[return-value]

    async def update_review(
        self, group_id: UUID, review_id: UUID, data: ReviewUpdate
    ) -> Review:
        review = await self.get_review(group_id, review_id)
        await self._require_active_member(group_id, data.user_id)
        if review.user_id != data.user_id:
            self._not_found("Review")
        changes = data.model_dump(exclude={"user_id"}, exclude_unset=True)
        for field, value in changes.items():
            setattr(review, field, value)
        return await self._save(review)

    async def create_vote(self, group_id: UUID, data: VoteCreate) -> Vote:
        await self.get_group(group_id)
        await self.get_book(data.book_id)
        await self._require_active_member(group_id, data.user_id)
        if await self.votes.get_for_user_book(group_id, data.user_id, data.book_id):
            self._conflict("User has already voted for this book in this group")
        vote = Vote(group_id=group_id, **data.model_dump())
        self.session.add(vote)
        return await self._save(vote)

    async def list_votes(self, group_id: UUID) -> list[Vote]:
        await self.get_group(group_id)
        return await self.votes.list_for_group(group_id)

    async def remove_vote(self, group_id: UUID, vote_id: UUID) -> None:
        await self.get_group(group_id)
        vote = await self.votes.get(vote_id)
        if vote is None or vote.group_id != group_id:
            self._not_found("Vote")
        await self.session.delete(vote)
        await self._commit()

    async def create_selection(
        self, group_id: UUID, data: SelectionCreate
    ) -> Selection:
        await self.get_group(group_id)
        await self._require_active_admin(group_id, data.requested_by_user_id)
        candidate_book_ids = await self.votes.list_candidate_book_ids(group_id)
        if not candidate_book_ids:
            self._conflict("No voted-for books are available to select")
        book_id = self.selection_strategy(candidate_book_ids)
        if book_id not in candidate_book_ids:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Selection strategy chose an ineligible book",
            )
        selection = Selection(
            group_id=group_id,
            book_id=book_id,
            requested_by_user_id=data.requested_by_user_id,
            candidate_count=len(candidate_book_ids),
            candidate_book_ids=[
                str(candidate_id) for candidate_id in candidate_book_ids
            ],
        )
        self.session.add(selection)
        return await self._save(selection)

    async def list_selections(self, group_id: UUID) -> list[Selection]:
        await self.get_group(group_id)
        return await self.selections.list_for_group(group_id)

    async def get_latest_selection(self, group_id: UUID) -> Selection:
        await self.get_group(group_id)
        selection = await self.selections.latest_for_group(group_id)
        if selection is None:
            self._not_found("Selection")
        return selection  # type: ignore[return-value]

    async def _require_active_member(self, group_id: UUID, user_id: UUID) -> None:
        user = await self.get_user(user_id)
        if not user.is_active or await self.memberships.get(group_id, user_id) is None:
            self._not_found("Membership")

    async def _require_active_admin(self, group_id: UUID, user_id: UUID) -> None:
        user = await self.get_user(user_id)
        membership = await self.memberships.get(group_id, user_id)
        if (
            not user.is_active
            or membership is None
            or membership.role != MembershipRole.ADMIN
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="An active group admin is required to select a book",
            )

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
