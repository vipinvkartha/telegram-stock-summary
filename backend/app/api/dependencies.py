from collections.abc import AsyncIterator, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import LLMProvider
from app.config import Settings


async def get_app_settings() -> Settings:
    raise RuntimeError("Application settings dependency was not configured")


async def get_llm_provider() -> LLMProvider:
    raise RuntimeError("LLM provider dependency was not configured")


async def get_app_session() -> AsyncIterator[AsyncSession]:
    raise RuntimeError("Database session dependency was not configured")


def session_dependency(
    session_factory: async_sessionmaker[AsyncSession],
) -> Callable[[], AsyncIterator[AsyncSession]]:
    async def _get_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    return _get_session
