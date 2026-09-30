"""End-to-end API coverage against the dedicated PostgreSQL database."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from reading_club.models import Membership, Selection, User, Vote

pytestmark = pytest.mark.integration


async def test_database_is_reachable_and_migrated(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        connectivity = await session.execute(text("SELECT 1"))
        if connectivity.scalar_one() != 1:
            pytest.fail("PostgreSQL connectivity check failed")
        table = await session.execute(
            text("SELECT to_regclass('public.selections')")
        )
        if table.scalar_one() != "selections":
            pytest.fail("Alembic schema does not contain selections")


async def test_complete_reading_club_flow_persists_postgresql_records(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    user_response = await client.post(
        "/api/v1/users",
        json={"email": "admin@example.com", "display_name": "Admin"},
    )
    user = user_response.json()
    group_response = await client.post(
        "/api/v1/groups", json={"name": "Postgres Readers"}
    )
    group = group_response.json()
    membership = await client.post(
        f"/api/v1/groups/{group['id']}/members",
        json={"user_id": user["id"], "role": "admin"},
    )
    assert membership.status_code == 201
    book_response = await client.post(
        "/api/v1/books",
        json={"title": "Database Internals", "author": "A. Author"},
    )
    book = book_response.json()
    vote = await client.post(
        f"/api/v1/groups/{group['id']}/votes",
        json={"user_id": user["id"], "book_id": book["id"]},
    )
    assert vote.status_code == 201
    selection = await client.post(
        f"/api/v1/groups/{group['id']}/selections",
        json={"requested_by_user_id": user["id"]},
    )
    assert selection.status_code == 201
    assert selection.json()["book_id"] == book["id"]

    async with session_factory() as session:
        assert (await session.scalars(select(Membership))).one().role.value == "admin"
        stored_vote = (await session.scalars(select(Vote))).one()
        assert stored_vote.book_id.hex == book["id"].replace("-", "")
        stored = (await session.scalars(select(Selection))).one()
        assert stored.candidate_count == 1
        assert stored.candidate_book_ids == [book["id"]]


async def test_postgresql_unique_constraint_rolls_back_and_session_recovers(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    async with session_factory() as session:
        session.add(User(email="unique@example.com", display_name="First"))
        await session.commit()
        session.add(User(email="unique@example.com", display_name="Duplicate"))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        assert len((await session.scalars(select(User))).all()) == 1

    response = await client.post(
        "/api/v1/users", json={"email": "usable@example.com", "display_name": "Usable"}
    )
    assert response.status_code == 201
