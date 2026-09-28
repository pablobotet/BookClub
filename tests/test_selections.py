# ruff: noqa: E501

import importlib.util
from collections.abc import AsyncGenerator
from pathlib import Path
from types import ModuleType
from typing import cast
from uuid import uuid4

import pytest
import sqlalchemy as sa
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Table
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from reading_club.api.v1.router import get_service
from reading_club.db import Base, get_db_session
from reading_club.main import app
from reading_club.models import Selection
from reading_club.services import ReadingClubService


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def create_user(client: AsyncClient, email: str, active: bool = True) -> dict[str, object]:
    response = await client.post(
        "/api/v1/users",
        json={"email": email, "display_name": email, "is_active": active},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def setup_group_with_admin(
    client: AsyncClient, active: bool = True, name: str = "Selectors"
) -> tuple[dict[str, object], dict[str, object]]:
    group_response = await client.post("/api/v1/groups", json={"name": name})
    assert group_response.status_code == 201
    group = cast(dict[str, object], group_response.json())
    admin = await create_user(client, f"{name.lower().replace(' ', '-')}@example.com", active)
    assert (await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": admin["id"], "role": "admin"})).status_code == 201
    return group, admin


async def add_book_and_vote(client: AsyncClient, group_id: object, user_id: object, title: str) -> dict[str, object]:
    book_response = await client.post("/api/v1/books", json={"title": title, "author": "Author"})
    assert book_response.status_code == 201
    book = cast(dict[str, object], book_response.json())
    assert (await client.post(f"/api/v1/groups/{group_id}/votes", json={"user_id": user_id, "book_id": book["id"]})).status_code == 201
    return book


async def test_selection_rejects_no_candidates_and_unauthorized_requesters(client: AsyncClient) -> None:
    group, admin = await setup_group_with_admin(client)
    assert (await client.get(f"/api/v1/groups/{group['id']}/selections/latest")).status_code == 404
    assert (await client.post(f"/api/v1/groups/{group['id']}/selections", json={"requested_by_user_id": admin["id"]})).status_code == 409
    member = await create_user(client, "member@example.com")
    assert (await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": member["id"]})).status_code == 201
    assert (await client.post(f"/api/v1/groups/{group['id']}/selections", json={"requested_by_user_id": member["id"]})).status_code == 403
    inactive_group, inactive_admin = await setup_group_with_admin(
        client, active=False, name="Inactive selectors"
    )
    assert (await client.post(f"/api/v1/groups/{inactive_group['id']}/selections", json={"requested_by_user_id": inactive_admin["id"]})).status_code == 403
    assert (await client.post("/api/v1/groups/00000000-0000-0000-0000-000000000000/selections", json={"requested_by_user_id": admin["id"]})).status_code == 404
    assert (await client.post(f"/api/v1/groups/{group['id']}/selections", json={"requested_by_user_id": "00000000-0000-0000-0000-000000000000"})).status_code == 404


async def test_selections_are_distinct_snapshots_with_history_and_latest(client: AsyncClient) -> None:
    group, admin = await setup_group_with_admin(client)
    first = await add_book_and_vote(client, group["id"], admin["id"], "First")
    second = await add_book_and_vote(client, group["id"], admin["id"], "Second")
    voter = await create_user(client, "second-voter@example.com")
    assert (await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": voter["id"]})).status_code == 201
    assert (await client.post(f"/api/v1/groups/{group['id']}/votes", json={"user_id": voter["id"], "book_id": first["id"]})).status_code == 201
    payload = {"requested_by_user_id": admin["id"]}
    created = await client.post(f"/api/v1/groups/{group['id']}/selections", json=payload)
    assert created.status_code == 201
    selection = created.json()
    assert selection["candidate_count"] == 2
    assert set(selection["candidate_book_ids"]) == {first["id"], second["id"]}
    assert selection["book_id"] in selection["candidate_book_ids"]
    repeated = await client.post(f"/api/v1/groups/{group['id']}/selections", json=payload)
    assert repeated.status_code == 201
    history = (await client.get(f"/api/v1/groups/{group['id']}/selections")).json()
    assert [item["id"] for item in history] == [repeated.json()["id"], selection["id"]]
    assert (await client.get(f"/api/v1/groups/{group['id']}/selections/latest")).json()["id"] == repeated.json()["id"]
    assert len((await client.get(f"/api/v1/groups/{group['id']}/votes")).json()) == 3


def test_selection_model_and_migration_match() -> None:
    table = cast(Table, Selection.__table__)
    assert set(table.c.keys()) == {
        "id", "group_id", "book_id", "requested_by_user_id", "candidate_count",
        "candidate_book_ids", "created_at",
    }
    assert isinstance(table.c.candidate_book_ids.type, sa.JSON)
    assert {constraint.name for constraint in table.constraints} >= {"ck_selections_candidate_count"}

    class Operations:
        def __init__(self) -> None:
            self.items: tuple[object, ...] = ()
            self.indexes: list[tuple[str, str, tuple[str, ...], bool]] = []

        def create_table(self, name: str, *items: object) -> None:
            assert name == "selections"
            self.items = items

        def create_index(
            self, name: str, table_name: str, columns: list[str], unique: bool
        ) -> None:
            self.indexes.append((name, table_name, tuple(columns), unique))

        @staticmethod
        def f(name: str) -> str:
            return name

    migration_path = (
        Path(__file__).parents[1] / "alembic/versions/20260928_0003_selections.py"
    )
    spec = importlib.util.spec_from_file_location("milestone_four", migration_path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    assert isinstance(migration, ModuleType)
    spec.loader.exec_module(migration)
    operations = Operations()
    setattr(migration, "op", operations)
    migration.upgrade()
    assert {item.name for item in operations.items if isinstance(item, sa.Column)} == set(
        table.c.keys()
    )
    assert set(operations.indexes) == {
        (index.name, table.name, tuple(index.columns.keys()), index.unique)
        for index in table.indexes
    }


async def test_selection_strategy_is_injectable_and_selects_from_snapshot(client: AsyncClient) -> None:
    group, admin = await setup_group_with_admin(client)
    await add_book_and_vote(client, group["id"], admin["id"], "First")
    second = await add_book_and_vote(client, group["id"], admin["id"], "Second")
    original = app.dependency_overrides.get(get_service)

    def deterministic_service(
        session: AsyncSession = Depends(get_db_session),
    ) -> ReadingClubService:
        return ReadingClubService(session, selection_strategy=lambda candidates: candidates[0])

    app.dependency_overrides[get_service] = deterministic_service
    try:
        response = await client.post(f"/api/v1/groups/{group['id']}/selections", json={"requested_by_user_id": admin["id"]})
    finally:
        if original is None:
            app.dependency_overrides.pop(get_service)
        else:
            app.dependency_overrides[get_service] = original
    assert response.status_code == 201
    assert response.json()["book_id"] == response.json()["candidate_book_ids"][0]
    assert response.json()["book_id"] in response.json()["candidate_book_ids"]
    assert second["id"] in response.json()["candidate_book_ids"]


async def test_ineligible_selection_strategy_returns_controlled_error_without_persisting(
    client: AsyncClient,
) -> None:
    group, admin = await setup_group_with_admin(client)
    await add_book_and_vote(client, group["id"], admin["id"], "Candidate")
    original = app.dependency_overrides.get(get_service)

    def invalid_strategy_service(
        session: AsyncSession = Depends(get_db_session),
    ) -> ReadingClubService:
        return ReadingClubService(session, selection_strategy=lambda candidates: uuid4())

    app.dependency_overrides[get_service] = invalid_strategy_service
    try:
        response = await client.post(
            f"/api/v1/groups/{group['id']}/selections",
            json={"requested_by_user_id": admin["id"]},
        )
    finally:
        if original is None:
            app.dependency_overrides.pop(get_service)
        else:
            app.dependency_overrides[get_service] = original

    assert response.status_code == 500
    assert response.json() == {"detail": "Selection strategy chose an ineligible book"}
    assert (await client.get(f"/api/v1/groups/{group['id']}/selections")).json() == []
