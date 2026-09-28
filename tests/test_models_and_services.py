import importlib.util
from pathlib import Path
from types import ModuleType
from typing import cast
from unittest.mock import AsyncMock

import pytest
import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy import Enum, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError

from reading_club.models import Book, Membership, MembershipRole, Review, User, Vote
from reading_club.services import ReadingClubService


def test_membership_enum_persists_lowercase_values_for_postgresql() -> None:
    role_type = Membership.__table__.c.role.type

    assert isinstance(role_type, Enum)
    assert role_type.enums == [role.value for role in MembershipRole]
    postgres_role_type = cast(
        postgresql.ENUM, role_type.dialect_impl(postgresql.dialect())
    )
    assert postgres_role_type.enums == ["member", "admin"]


def test_books_reviews_and_votes_define_portable_constraints() -> None:
    assert Book.__table__.c.isbn.unique is True
    review_table = cast(Table, Review.__table__)
    vote_table = cast(Table, Vote.__table__)
    assert {constraint.name for constraint in review_table.constraints} >= {
        "ck_reviews_rating_range",
        "uq_reviews_user_group_book",
    }
    assert {constraint.name for constraint in vote_table.constraints} >= {
        "uq_votes_user_group_book"
    }


def test_milestone_three_migration_matches_model_structure() -> None:
    class Operations:
        def __init__(self) -> None:
            self.tables: dict[str, tuple[object, ...]] = {}
            self.indexes: list[tuple[str, str, tuple[str, ...], bool]] = []

        def create_table(self, name: str, *items: object) -> None:
            self.tables[name] = items

        def create_index(
            self, name: str, table_name: str, columns: list[str], unique: bool
        ) -> None:
            self.indexes.append((name, table_name, tuple(columns), unique))

        @staticmethod
        def f(name: str) -> str:
            return name

    migration_path = (
        Path(__file__).parents[1]
        / "alembic/versions/20260928_0002_books_reviews_votes.py"
    )
    spec = importlib.util.spec_from_file_location("milestone_three", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    assert isinstance(migration, ModuleType)
    spec.loader.exec_module(migration)
    operations = Operations()
    setattr(migration, "op", operations)
    migration.upgrade()

    expected = {"books": Book, "reviews": Review, "votes": Vote}
    assert set(operations.tables) == set(expected)
    for name, model in expected.items():
        items = operations.tables[name]
        migration_columns = {
            item.name for item in items if isinstance(item, sa.Column)
        }
        assert migration_columns == set(model.__table__.c.keys())
        migration_constraints = {
            item.name
            for item in items
            if isinstance(item, (sa.CheckConstraint, sa.UniqueConstraint))
        }
        model_constraints = {
            constraint.name
            for constraint in cast(Table, model.__table__).constraints
            if isinstance(constraint, (sa.CheckConstraint, sa.UniqueConstraint))
        }
        assert migration_constraints == model_constraints
        migration_foreign_keys = {
            foreign_key.target_fullname
            for item in items
            if isinstance(item, sa.ForeignKeyConstraint)
            for foreign_key in item.elements
        }
        model_foreign_keys = {
            foreign_key.target_fullname
            for foreign_key in model.__table__.foreign_keys
        }
        assert migration_foreign_keys == model_foreign_keys

    assert set(operations.indexes) == {
        (
            index.name,
            cast(Table, index.table).name,
            tuple(index.columns.keys()),
            index.unique,
        )
        for model in (Review, Vote)
        for index in cast(Table, model.__table__).indexes
    }


async def test_integrity_error_rolls_back_and_returns_conflict() -> None:
    session = AsyncMock()
    session.commit.side_effect = IntegrityError("insert", {}, Exception("duplicate"))
    service = ReadingClubService(session)

    with pytest.raises(HTTPException) as error:
        await service._save(User(email="reader@example.com", display_name="Reader"))

    assert error.value.status_code == 409
    session.rollback.assert_awaited_once()
    session.refresh.assert_not_awaited()
