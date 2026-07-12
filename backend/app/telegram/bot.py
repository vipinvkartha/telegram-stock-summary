from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import LLMProvider
from app.config import Settings
from app.repositories.watchlists import WatchlistRepository
from app.services import ReportService, WatchlistService

logger = structlog.get_logger(__name__)


class TelegramBotService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: async_sessionmaker[AsyncSession],
        provider: LLMProvider,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.provider = provider
        self._application: Any | None = None

    async def start(self) -> None:
        if not self.settings.telegram_bot_enabled:
            logger.info("telegram_bot_disabled")
            return

        try:
            from telegram.ext import ApplicationBuilder, CommandHandler
        except ImportError as exc:
            raise RuntimeError("Install python-telegram-bot to use bot commands") from exc

        application = ApplicationBuilder().token(self.settings.bot_token).build()
        application.add_handler(CommandHandler("start", self._start))
        application.add_handler(CommandHandler("help", self._help))
        application.add_handler(CommandHandler("report", self._report))
        application.add_handler(CommandHandler("summary", self._report))
        application.add_handler(CommandHandler("watchlist", self._watchlist))
        application.add_handler(CommandHandler("add", self._add))
        application.add_handler(CommandHandler("remove", self._remove))
        application.add_handler(CommandHandler("settings", self._settings))
        application.add_handler(CommandHandler("history", self._history))

        await application.initialize()
        await application.start()
        if application.updater:
            await application.updater.start_polling()
        self._application = application
        logger.info("telegram_bot_started")

    async def stop(self) -> None:
        if not self._application:
            return
        if self._application.updater:
            await self._application.updater.stop()
        await self._application.stop()
        await self._application.shutdown()
        logger.info("telegram_bot_stopped")

    async def _start(self, update: Any, context: Any) -> None:
        await update.message.reply_text(
            "Welcome. I track configured stock channels and generate AI market summaries."
        )

    async def _help(self, update: Any, context: Any) -> None:
        await update.message.reply_text(
            "/report - latest report\n"
            "/summary - latest report\n"
            "/watchlist - show tracked tickers\n"
            "/add TSLA - add a ticker\n"
            "/remove TSLA - remove a ticker\n"
            "/settings - show report settings\n"
            "/history - recent report titles"
        )

    async def _report(self, update: Any, context: Any) -> None:
        async with self.session_factory() as session:
            service = ReportService(session, self.provider, self.settings)
            report = await service.latest()
            if not report:
                await update.message.reply_text("No reports generated yet.")
                return
            for chunk in _telegram_chunks(report.body):
                await update.message.reply_text(chunk)

    async def _watchlist(self, update: Any, context: Any) -> None:
        async with self.session_factory() as session:
            user = await _bot_user(session, update)
            service = WatchlistService(session)
            stocks = await service.list_default(user)
            await session.commit()
            text = ", ".join(stock.ticker for stock in stocks) or "Your watchlist is empty."
            await update.message.reply_text(text)

    async def _add(self, update: Any, context: Any) -> None:
        ticker = _first_arg(context)
        if not ticker:
            await update.message.reply_text("Usage: /add TSLA")
            return
        async with self.session_factory() as session:
            user = await _bot_user(session, update)
            stock = await WatchlistService(session).add(ticker, user)
            await session.commit()
            await update.message.reply_text(f"Added {stock.ticker}.")

    async def _remove(self, update: Any, context: Any) -> None:
        ticker = _first_arg(context)
        if not ticker:
            await update.message.reply_text("Usage: /remove TSLA")
            return
        async with self.session_factory() as session:
            user = await _bot_user(session, update)
            removed = await WatchlistService(session).remove(ticker, user)
            await session.commit()
            await update.message.reply_text(
                f"Removed {ticker.upper()}." if removed else "Ticker not found."
            )

    async def _settings(self, update: Any, context: Any) -> None:
        await update.message.reply_text(
            "Report times: "
            + ", ".join(self.settings.report_times)
            + f"\nTimezone: {self.settings.report_timezone}"
        )

    async def _history(self, update: Any, context: Any) -> None:
        async with self.session_factory() as session:
            service = ReportService(session, self.provider, self.settings)
            report = await service.latest()
            if not report:
                await update.message.reply_text("No report history yet.")
                return
            await update.message.reply_text(
                f"Latest: {report.title} at {report.report_date.isoformat()}"
            )


async def _bot_user(session: AsyncSession, update: Any) -> Any:
    effective_user = update.effective_user
    repo = WatchlistRepository(session)
    return await repo.get_or_create_user(
        telegram_user_id=effective_user.id,
        username=effective_user.username,
        first_name=effective_user.first_name,
    )


def _first_arg(context: Any) -> str | None:
    if not getattr(context, "args", None):
        return None
    return str(context.args[0]).upper().lstrip("$")


def _telegram_chunks(text: str, limit: int = 3800) -> list[str]:
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at == -1:
            split_at = limit
        chunks.append(remaining[:split_at])
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks
