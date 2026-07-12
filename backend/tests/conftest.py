from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.database.base import Base


@dataclass
class RawMessageStub:
    id: int
    channel_id: int
    text: str
    timestamp: datetime
    links: list[str]
    forwarded_from: str | None = None


@pytest.fixture
def raw_message_factory():
    def _factory(message_id: int, text: str) -> RawMessageStub:
        return RawMessageStub(
            id=message_id,
            channel_id=1,
            text=text,
            timestamp=datetime(2026, 7, 8, tzinfo=UTC),
            links=[],
        )

    return _factory


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
