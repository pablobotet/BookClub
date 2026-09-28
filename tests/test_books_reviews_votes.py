# ruff: noqa: E501

from collections.abc import AsyncGenerator
from typing import cast

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


async def create_user(
    client: AsyncClient, email: str, active: bool = True
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/users",
        json={"email": email, "display_name": email, "is_active": active},
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_group(client: AsyncClient) -> dict[str, object]:
    response = await client.post("/api/v1/groups", json={"name": "Readers"})
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def create_book(client: AsyncClient) -> dict[str, object]:
    response = await client.post(
        "/api/v1/books",
        json={
            "title": " Book ",
            "author": " Author ",
            "isbn": " 978-1 ",
            "publication_year": 1,
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


async def test_books_crud_duplicates_and_validation(client: AsyncClient) -> None:
    book = await create_book(client)
    assert book["title"] == "Book"
    assert book["author"] == "Author"
    assert book["isbn"] == "9781"
    assert book["publication_year"] == 1
    assert (await client.get("/api/v1/books")).json()[0]["id"] == book["id"]
    assert (await client.get(f"/api/v1/books/{book['id']}")).status_code == 200
    updated = await client.patch(f"/api/v1/books/{book['id']}", json={"isbn": "978 1"})
    assert updated.status_code == 200
    assert updated.json()["isbn"] == "9781"
    assert (
        await client.post(
            "/api/v1/books", json={"title": "Other", "author": "Other", "isbn": "978 1"}
        )
    ).status_code == 409
    assert (await client.post("/api/v1/books", json={"title": " ", "author": "A"})).status_code == 422
    for publication_year in (True, 0, -1):
        assert (
            await client.post(
                "/api/v1/books",
                json={"title": "Invalid", "author": "Author", "publication_year": publication_year},
            )
        ).status_code == 422
        assert (
            await client.patch(
                f"/api/v1/books/{book['id']}",
                json={"publication_year": publication_year},
            )
        ).status_code == 422
    assert (await client.patch(f"/api/v1/books/{book['id']}", json={})).status_code == 422
    assert (await client.get("/api/v1/books/00000000-0000-0000-0000-000000000000")).status_code == 404


async def test_review_lifecycle_membership_and_missing_parents(client: AsyncClient) -> None:
    user, group, book = await create_user(client, "reviewer@example.com"), await create_group(client), await create_book(client)
    payload = {"user_id": user["id"], "book_id": book["id"], "rating": 4, "text": "Nice"}
    assert (await client.post(f"/api/v1/groups/{group['id']}/reviews", json=payload)).status_code == 404
    assert (await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": user["id"]})).status_code == 201
    created = await client.post(f"/api/v1/groups/{group['id']}/reviews", json=payload)
    assert created.status_code == 201
    review = created.json()
    assert (await client.get(f"/api/v1/groups/{group['id']}/reviews")).json()[0]["id"] == review["id"]
    assert (await client.get(f"/api/v1/groups/{group['id']}/reviews/{review['id']}")).status_code == 200
    assert (await client.patch(f"/api/v1/groups/{group['id']}/reviews/{review['id']}", json={"user_id": user["id"], "rating": 5})).json()["rating"] == 5
    assert (await client.post(f"/api/v1/groups/{group['id']}/reviews", json=payload)).status_code == 409
    assert (await client.post(f"/api/v1/groups/{group['id']}/reviews", json={**payload, "book_id": "00000000-0000-0000-0000-000000000000"})).status_code == 404
    assert (await client.post("/api/v1/groups/00000000-0000-0000-0000-000000000000/reviews", json=payload)).status_code == 404
    assert (await client.post(f"/api/v1/groups/{group['id']}/reviews", json={**payload, "rating": 6})).status_code == 422
    inactive = await create_user(client, "inactive-reviewer@example.com", active=False)
    assert (
        await client.post(
            f"/api/v1/groups/{group['id']}/members",
            json={"user_id": inactive["id"]},
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/v1/groups/{group['id']}/reviews",
            json={**payload, "user_id": inactive["id"]},
        )
    ).status_code == 404


async def test_votes_lifecycle_duplicate_and_inactive_rejection(client: AsyncClient) -> None:
    user, group, book = await create_user(client, "voter@example.com"), await create_group(client), await create_book(client)
    await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": user["id"]})
    payload = {"user_id": user["id"], "book_id": book["id"]}
    created = await client.post(f"/api/v1/groups/{group['id']}/votes", json=payload)
    assert created.status_code == 201
    vote = created.json()
    assert (await client.get(f"/api/v1/groups/{group['id']}/votes")).json()[0]["id"] == vote["id"]
    assert (await client.post(f"/api/v1/groups/{group['id']}/votes", json=payload)).status_code == 409
    assert (await client.delete(f"/api/v1/groups/{group['id']}/votes/{vote['id']}")).status_code == 204
    assert (await client.delete(f"/api/v1/groups/{group['id']}/votes/{vote['id']}")).status_code == 404
    inactive = await create_user(client, "inactive@example.com", active=False)
    await client.post(f"/api/v1/groups/{group['id']}/members", json={"user_id": inactive["id"]})
    assert (await client.post(f"/api/v1/groups/{group['id']}/votes", json={"user_id": inactive["id"], "book_id": book["id"]})).status_code == 404
