from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from reading_club.models import Membership, MembershipRole, User
from reading_club.services import ReadingClubService


def test_membership_enum_persists_lowercase_values_for_postgresql() -> None:
    role_type = Membership.__table__.c.role.type

    assert isinstance(role_type, Enum)
    assert role_type.enums == [role.value for role in MembershipRole]
    postgres_role_type = cast(
        postgresql.ENUM, role_type.dialect_impl(postgresql.dialect())
    )
    assert postgres_role_type.enums == ["member", "admin"]


async def test_integrity_error_rolls_back_and_returns_conflict() -> None:
    session = AsyncMock()
    session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    service = ReadingClubService(session)

    with pytest.raises(HTTPException) as error:
        await service._save(User(email="reader@example.com", display_name="Reader"))

    assert error.value.status_code == 409
    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()
