"""Fixtures for isolated PostgreSQL integration tests.

These tests truncate a shared database and must not run concurrently against it.
"""

import os
from collections.abc import AsyncGenerator
from typing import Any, Callable, cast

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from reading_club.db import get_db_session
from reading_club.main import app

TEST_DATABASE_NAME = "reading_club_test"
TABLES = "selections, votes, reviews, memberships, books, reading_groups, users"


class MissingOverride:
    """Distinguish an absent dependency override from an installed callable."""


MISSING_OVERRIDE = MissingOverride()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip explicitly marked PostgreSQL tests when no safe URL is configured."""
    if os.environ.get("TEST_DATABASE_URL"):
        return
    reason = (
        "TEST_DATABASE_URL is not configured; PostgreSQL integration tests are skipped"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.skip(reason=reason))


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Return a validated URL for the one database integration tests may alter."""
    url = os.environ["TEST_DATABASE_URL"]
    parsed = make_url(url)
    if parsed.drivername not in {"postgresql", "postgresql+asyncpg"}:
        pytest.fail("TEST_DATABASE_URL must use PostgreSQL")
    if parsed.database != TEST_DATABASE_NAME:
        pytest.fail(f"TEST_DATABASE_URL must target {TEST_DATABASE_NAME}")
    return url


@pytest.fixture(scope="session")
async def engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Provide the migrated asyncpg engine after checking the Alembic revision."""
    engine = create_async_engine(test_database_url, poolclass=NullPool)
    expected = ScriptDirectory.from_config(Config("alembic.ini")).get_current_head()
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT version_num FROM alembic_version")
        )
        actual: str = result.scalar_one()
    if actual != expected:
        await engine.dispose()
        pytest.fail(
            "reading_club_test is not at Alembic head; run scripts/setup_test_db.sh"
        )
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def clean_database(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Truncate application tables while retaining Alembic's version table."""
    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE")
        )
    yield
    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {TABLES} RESTART IDENTITY CASCADE")
        )


@pytest.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build request sessions bound to the isolated PostgreSQL database."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Exercise the FastAPI application using PostgreSQL rather than SQLite."""
    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    previous_override: Callable[..., Any] | MissingOverride = (
        app.dependency_overrides.get(get_db_session, MISSING_OVERRIDE)
    )
    app.dependency_overrides[get_db_session] = override_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as test_client:
            yield test_client
    finally:
        if previous_override is MISSING_OVERRIDE:
            app.dependency_overrides.pop(get_db_session, None)
        else:
            app.dependency_overrides[get_db_session] = cast(
                Callable[..., Any], previous_override
            )
