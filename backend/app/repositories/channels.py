from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Channel


class ChannelRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_enabled(self) -> list[Channel]:
        result = await self.session.scalars(select(Channel).where(Channel.enabled.is_(True)))
        return list(result)

    async def get_by_username(self, username: str) -> Channel | None:
        normalized = username.lstrip("@").strip()
        result = await self.session.scalars(select(Channel).where(Channel.username == normalized))
        return result.first()

    async def get_or_create(
        self,
        *,
        name: str,
        username: str | None = None,
        telegram_channel_id: int | None = None,
        enabled: bool = True,
    ) -> Channel:
        query = select(Channel)
        if telegram_channel_id is not None:
            query = query.where(Channel.telegram_channel_id == telegram_channel_id)
        elif username:
            query = query.where(Channel.username == username.lstrip("@"))
        else:
            query = query.where(Channel.name == name)

        existing = (await self.session.scalars(query)).first()
        if existing:
            existing.name = name or existing.name
            existing.username = username.lstrip("@") if username else existing.username
            existing.telegram_channel_id = telegram_channel_id or existing.telegram_channel_id
            existing.enabled = enabled
            return existing

        channel = Channel(
            name=name,
            username=username.lstrip("@") if username else None,
            telegram_channel_id=telegram_channel_id,
            enabled=enabled,
        )
        self.session.add(channel)
        await self.session.flush()
        return channel
