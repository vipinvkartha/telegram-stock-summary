from datetime import datetime

from sqlalchemy import Select, and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, *, channel_id: int, telegram_message_id: int) -> bool:
        query = select(Message.id).where(
            Message.channel_id == channel_id,
            Message.telegram_message_id == telegram_message_id,
        )
        return (await self.session.scalar(query)) is not None

    async def add(
        self,
        *,
        channel_id: int,
        telegram_message_id: int,
        timestamp: datetime,
        text: str,
        author: str | None = None,
        media_type: str | None = None,
        links: list[str] | None = None,
        normalized_text: str | None = None,
        content_hash: str | None = None,
        forwarded_from: str | None = None,
    ) -> Message:
        message = Message(
            channel_id=channel_id,
            telegram_message_id=telegram_message_id,
            timestamp=timestamp,
            author=author,
            text=text,
            media_type=media_type,
            links=links or [],
            normalized_text=normalized_text,
            content_hash=content_hash,
            forwarded_from=forwarded_from,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def list_between(self, *, since: datetime, until: datetime) -> list[Message]:
        query: Select[tuple[Message]] = (
            select(Message)
            .where(and_(Message.timestamp >= since, Message.timestamp <= until))
            .options(selectinload(Message.channel), selectinload(Message.stock_mappings))
            .order_by(Message.timestamp.asc())
        )
        return list(await self.session.scalars(query))

    async def latest(self, limit: int = 50) -> list[Message]:
        query = select(Message).order_by(desc(Message.timestamp)).limit(limit)
        return list(await self.session.scalars(query))
