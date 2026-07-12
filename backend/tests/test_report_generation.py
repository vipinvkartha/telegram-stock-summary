from datetime import UTC, datetime, timedelta

import pytest

from app.ai.mock import MockLLMProvider
from app.config import Settings
from app.models import Channel
from app.repositories.messages import MessageRepository
from app.services.report_service import ReportService


@pytest.mark.asyncio
async def test_report_generation_persists_report(session_factory) -> None:
    async with session_factory() as session:
        channel = Channel(
            telegram_channel_id=123,
            name="Stocks Chat",
            username="stocks_chat",
            enabled=True,
        )
        session.add(channel)
        await session.flush()
        now = datetime.now(UTC)
        messages = MessageRepository(session)
        await messages.add(
            channel_id=channel.id,
            telegram_message_id=1,
            timestamp=now - timedelta(minutes=30),
            text="NVDA earnings beat and guidance upgrade looks bullish",
        )
        await messages.add(
            channel_id=channel.id,
            telegram_message_id=2,
            timestamp=now - timedelta(minutes=20),
            text="$TSLA downgrade risk has traders bearish",
        )
        await session.commit()

    async with session_factory() as session:
        service = ReportService(
            session,
            MockLLMProvider(),
            Settings(database_url="sqlite+aiosqlite:///:memory:"),
        )
        report = await service.generate(since=now - timedelta(hours=1), until=now)

        assert report.id is not None
        assert "NVDA" in report.body
        assert "TSLA" in report.body
        assert report.payload["stocks"]
