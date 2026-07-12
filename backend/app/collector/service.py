from datetime import UTC
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.processor.normalization import content_hash, extract_urls, normalize_text
from app.repositories import ChannelRepository, MessageRepository

logger = structlog.get_logger(__name__)


class TelegramCollectorService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self._client: Any | None = None
        self._stopping = False

    async def start(self) -> None:
        if not self.settings.telegram_collection_enabled:
            logger.info("telegram_collection_disabled")
            return

        try:
            from telethon import TelegramClient, events
            from telethon.errors import FloodWaitError
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise RuntimeError("Install telethon to use Telegram collection") from exc

        if not self.settings.telegram_session_string and not Path(
            self.settings.session_file
        ).exists():
            logger.error(
                "telegram_session_missing",
                message="Generate TELEGRAM_SESSION_STRING and set it in Railway.",
            )
            return

        session = (
            StringSession(self.settings.telegram_session_string)
            if self.settings.telegram_session_string
            else self.settings.session_file
        )
        client = TelegramClient(
            session,
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )
        self._client = client

        @client.on(events.NewMessage(chats=self.settings.telegram_channels))
        async def handle_new_message(event: Any) -> None:
            try:
                await self._store_event(event)
            except FloodWaitError as exc:
                logger.warning("telegram_rate_limited", seconds=exc.seconds)
            except Exception:
                logger.exception("telegram_message_store_failed")

        while not self._stopping:
            try:
                logger.info(
                    "telegram_collector_connecting", channels=self.settings.telegram_channels
                )
                await _connect_authorized(client)
                await self._ensure_configured_channels(client)
                logger.info("telegram_collector_connected")
                await client.run_until_disconnected()
            except FloodWaitError as exc:
                logger.warning("telegram_rate_limited", seconds=exc.seconds)
                await client.disconnect()
            except Exception:
                logger.exception("telegram_collector_disconnected")
                await client.disconnect()
                if not self._stopping:
                    import asyncio

                    await asyncio.sleep(10)

    async def stop(self) -> None:
        self._stopping = True
        if self._client is not None:
            await self._client.disconnect()

    async def backfill(self, *, limit_per_channel: int) -> dict[str, Any]:
        if not self.settings.telegram_collection_enabled:
            return {
                "channels": [],
                "total_seen": 0,
                "total_stored": 0,
                "message": "Telegram collection is not configured.",
            }

        try:
            from telethon import TelegramClient
            from telethon.sessions import StringSession
        except ImportError as exc:
            raise RuntimeError("Install telethon to use Telegram collection") from exc

        owned_client = False
        client = self._client
        if client is None or not client.is_connected():
            if not self.settings.telegram_session_string and not Path(
                self.settings.session_file
            ).exists():
                raise RuntimeError(
                    "Telegram session is missing. Set TELEGRAM_SESSION_STRING in Railway."
                )
            session = (
                StringSession(self.settings.telegram_session_string)
                if self.settings.telegram_session_string
                else self.settings.session_file
            )
            client = TelegramClient(
                session,
                self.settings.telegram_api_id,
                self.settings.telegram_api_hash,
            )
            owned_client = True

        await _connect_authorized(client)
        try:
            results: list[dict[str, Any]] = []
            total_seen = 0
            total_stored = 0
            for configured in self.settings.telegram_channels:
                entity = await client.get_entity(configured)
                seen = 0
                stored = 0
                async for message in client.iter_messages(entity, limit=limit_per_channel):
                    seen += 1
                    if await self._store_message(message, entity):
                        stored += 1
                total_seen += seen
                total_stored += stored
                results.append(
                    {
                        "channel": configured,
                        "seen": seen,
                        "stored": stored,
                        "skipped": seen - stored,
                    }
                )
            return {
                "channels": results,
                "total_seen": total_seen,
                "total_stored": total_stored,
                "message": "Backfill completed.",
            }
        finally:
            if owned_client:
                await client.disconnect()

    async def _ensure_configured_channels(self, client: Any) -> None:
        async with self.session_factory() as session:
            channels = ChannelRepository(session)
            for configured in self.settings.telegram_channels:
                entity = await client.get_entity(configured)
                username = getattr(entity, "username", None) or configured.lstrip("@")
                name = getattr(entity, "title", None) or username
                telegram_channel_id = getattr(entity, "id", None)
                await channels.get_or_create(
                    name=name,
                    username=username,
                    telegram_channel_id=telegram_channel_id,
                    enabled=True,
                )
            await session.commit()

    async def _store_event(self, event: Any) -> None:
        message = event.message
        chat = await event.get_chat()
        await self._store_message(message, chat)

    async def _store_message(self, message: Any, chat: Any) -> bool:
        text = getattr(message, "message", None) or ""
        if not text.strip():
            return False
        telegram_channel_id = getattr(chat, "id", None)
        username = getattr(chat, "username", None)
        name = getattr(chat, "title", None) or username or str(telegram_channel_id)
        timestamp = message.date
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        async with self.session_factory() as session:
            channels = ChannelRepository(session)
            messages = MessageRepository(session)
            channel = await channels.get_or_create(
                name=name,
                username=username,
                telegram_channel_id=telegram_channel_id,
                enabled=True,
            )
            if await messages.exists(channel_id=channel.id, telegram_message_id=message.id):
                return False
            normalized = normalize_text(text, strip_emoji=self.settings.normalize_remove_emoji)
            try:
                await messages.add(
                    channel_id=channel.id,
                    telegram_message_id=message.id,
                    timestamp=timestamp,
                    author=str(getattr(message, "sender_id", None) or ""),
                    text=text,
                    normalized_text=normalized,
                    content_hash=content_hash(normalized),
                    media_type=_media_type(message),
                    links=extract_urls(text),
                    forwarded_from=_forwarded_from(message),
                )
                await session.commit()
                logger.info(
                    "telegram_message_stored",
                    channel=username or telegram_channel_id,
                    telegram_message_id=message.id,
                )
                return True
            except IntegrityError:
                await session.rollback()
                logger.info(
                    "telegram_duplicate_message_ignored",
                    channel=username or telegram_channel_id,
                    telegram_message_id=message.id,
                )
                return False


def _media_type(message: Any) -> str | None:
    if getattr(message, "photo", None):
        return "photo"
    if getattr(message, "video", None):
        return "video"
    if getattr(message, "document", None):
        return "document"
    return None


def _forwarded_from(message: Any) -> str | None:
    fwd = getattr(message, "fwd_from", None)
    if not fwd:
        return None
    return str(getattr(fwd, "from_name", None) or getattr(fwd, "from_id", None) or "")


async def _connect_authorized(client: Any) -> None:
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram collector session is not authorized. "
            "Generate TELEGRAM_SESSION_STRING and set it in Railway."
        )
