"""Déclaration des sessions."""

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from labomatics.core.config.settings import settings

engine = create_async_engine(
    settings.get_async_db_url(),
    echo=False,
    pool_pre_ping=True,
)

async_session_local = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession | Any, Any]:
    """Retourne la session SQL Async courante."""
    async with async_session_local() as session:
        yield session
