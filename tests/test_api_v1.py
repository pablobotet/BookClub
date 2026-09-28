from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from reading_club.db import Base, get_db_session
from reading_club.main import app


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
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def test_users_create_list_get_patch_and_handle_duplicates(
    client: AsyncClient,
) -> None:
    created = await client.post(
        "/api/v1/users",
        json={"email": " Reader@Example.COM ", "display_name": " Reader "},
    )

    assert created.status_code == 201
    user = created.json()
    assert user["email"] == "reader@example.com"
    assert user["display_name"] == "Reader"

    assert (await client.get("/api/v1/users")).json()[0]["id"] == user["id"]
    assert (await client.get(f"/api/v1/users/{user['id']}")).status_code == 200

    updated = await client.patch(
        f"/api/v1/users/{user['id']}",
        json={"display_name": "Updated", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated"
    assert updated.json()["is_active"] is False

    duplicate = await client.post(
        "/api/v1/users", json={"email": "READER@example.com", "display_name": "Other"}
    )
    assert duplicate.status_code == 409
    assert (
        await client.get("/api/v1/users/00000000-0000-0000-0000-000000000000")
    ).status_code == 404


async def test_groups_and_membership_lifecycle(client: AsyncClient) -> None:
    user = (
        await client.post(
            "/api/v1/users",
            json={"email": "member@example.com", "display_name": "Member"},
        )
    ).json()
    group = (
        await client.post(
            "/api/v1/groups", json={"name": " Poetry Club ", "description": "Weekly"}
        )
    ).json()

    assert (await client.get("/api/v1/groups")).json()[0]["id"] == group["id"]
    assert (await client.get(f"/api/v1/groups/{group['id']}")).status_code == 200
    updated = await client.patch(
        f"/api/v1/groups/{group['id']}", json={"description": None}
    )
    assert updated.status_code == 200
    assert updated.json()["description"] is None
    assert (
        await client.post("/api/v1/groups", json={"name": "Poetry Club"})
    ).status_code == 409

    other_group = (await client.post("/api/v1/groups", json={"name": "Fiction"})).json()
    assert (
        await client.patch(
            f"/api/v1/groups/{other_group['id']}", json={"name": "Poetry Club"}
        )
    ).status_code == 409

    added = await client.post(
        f"/api/v1/groups/{group['id']}/members",
        json={"user_id": user["id"], "role": "admin"},
    )
    assert added.status_code == 201
    assert added.json()["role"] == "admin"
    assert len((await client.get(f"/api/v1/groups/{group['id']}/members")).json()) == 1
    assert (
        await client.post(
            f"/api/v1/groups/{group['id']}/members", json={"user_id": user["id"]}
        )
    ).status_code == 409

    removed = await client.delete(f"/api/v1/groups/{group['id']}/members/{user['id']}")
    assert removed.status_code == 204
    assert (await client.get(f"/api/v1/groups/{group['id']}/members")).json() == []
    assert (
        await client.delete(f"/api/v1/groups/{group['id']}/members/{user['id']}")
    ).status_code == 404


async def test_group_validates_names_and_missing_resources(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/groups", json={"name": " "})).status_code == 422
    assert (
        await client.patch(
            "/api/v1/groups/00000000-0000-0000-0000-000000000000", json={"name": "New"}
        )
    ).status_code == 404
    assert (
        await client.patch(
            "/api/v1/groups/00000000-0000-0000-0000-000000000000", json={}
        )
    ).status_code == 422
    assert (
        await client.patch(
            "/api/v1/users/00000000-0000-0000-0000-000000000000", json={}
        )
    ).status_code == 422
    missing_group = "00000000-0000-0000-0000-000000000000"
    missing_user = "00000000-0000-0000-0000-000000000001"
    assert (
        await client.post(
            f"/api/v1/groups/{missing_group}/members", json={"user_id": missing_user}
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/groups/{missing_group}/members")
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/groups/{missing_group}/members/{missing_user}")
    ).status_code == 404
    group = (await client.post("/api/v1/groups", json={"name": "Existing"})).json()
    assert (
        await client.post(
            f"/api/v1/groups/{group['id']}/members", json={"user_id": missing_user}
        )
    ).status_code == 404
