"""Pydantic schemas for the version 1 reading-club API."""

from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

from reading_club.models import MembershipRole


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(APIModel):
    email: str
    display_name: str = Field(min_length=1, max_length=255)
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("email must not be empty")
        return normalized

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("display_name must not be empty")
        return normalized


class UserUpdate(APIModel):
    email: str | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return UserCreate.normalize_email(value) if value is not None else value

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        return UserCreate.normalize_display_name(value) if value is not None else value

    @model_validator(mode="after")
    def require_update(self) -> UserUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        return self


class UserResponse(APIModel):
    id: UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class GroupCreate(APIModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")
        return normalized


class GroupUpdate(APIModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return GroupCreate.normalize_name(value) if value is not None else value

    @model_validator(mode="after")
    def require_update(self) -> GroupUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        return self


class GroupResponse(APIModel):
    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class MembershipCreate(APIModel):
    user_id: UUID
    role: MembershipRole = MembershipRole.MEMBER


class MembershipResponse(APIModel):
    id: UUID
    user_id: UUID
    group_id: UUID
    role: MembershipRole
    joined_at: datetime


class BookCreate(APIModel):
    title: str = Field(min_length=1, max_length=255)
    author: str = Field(min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    publication_year: StrictInt | None = Field(default=None, ge=1)
    description: str | None = None

    @field_validator("title", "author")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("isbn")
    @classmethod
    def normalize_isbn(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = re.sub(r"[-\s]", "", value).upper()
        return normalized or None


class BookUpdate(APIModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    author: str | None = Field(default=None, min_length=1, max_length=255)
    isbn: str | None = Field(default=None, max_length=32)
    publication_year: StrictInt | None = Field(default=None, ge=1)
    description: str | None = None

    @field_validator("title", "author")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return BookCreate.normalize_text(value)

    @field_validator("isbn")
    @classmethod
    def normalize_isbn(cls, value: str | None) -> str | None:
        return BookCreate.normalize_isbn(value)

    @model_validator(mode="after")
    def require_update(self) -> BookUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        return self


class BookResponse(APIModel):
    id: UUID
    title: str
    author: str
    isbn: str | None
    publication_year: int | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class ReviewCreate(APIModel):
    book_id: UUID
    user_id: UUID
    rating: int = Field(ge=1, le=5)
    text: str | None = None


class ReviewUpdate(APIModel):
    user_id: UUID
    rating: int | None = Field(default=None, ge=1, le=5)
    text: str | None = None

    @model_validator(mode="after")
    def require_update(self) -> ReviewUpdate:
        if not ({"rating", "text"} & self.model_fields_set):
            raise ValueError("at least one field must be supplied")
        return self


class ReviewResponse(APIModel):
    id: UUID
    group_id: UUID
    book_id: UUID
    user_id: UUID
    rating: int
    text: str | None
    created_at: datetime
    updated_at: datetime


class VoteCreate(APIModel):
    book_id: UUID
    user_id: UUID


class VoteResponse(APIModel):
    id: UUID
    group_id: UUID
    book_id: UUID
    user_id: UUID
    created_at: datetime
