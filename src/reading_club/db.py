"""Asynchronous database engine and session dependencies."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from reading_club.config import get_settings


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


engine = create_async_engine(get_settings().database_url)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an asynchronous database session for a request."""
    async with async_session_factory() as session:
        yield session
