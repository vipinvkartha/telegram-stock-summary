import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.ai import LLMProvider, build_llm_provider
from app.api import router
from app.api.dependencies import (
    get_app_session,
    get_app_settings,
    get_llm_provider,
    session_dependency,
)
from app.collector import TelegramCollectorService
from app.config import Settings, get_settings
from app.config.logging import configure_logging
from app.database.base import Base
from app.scheduler import SchedulerService
from app.telegram import TelegramBotService

logger = structlog.get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider = build_llm_provider(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        runtime = await _start_runtime(settings, engine, session_factory, provider)
        app.state.runtime = runtime
        try:
            yield
        finally:
            await runtime.stop()
            await engine.dispose()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.include_router(router)
    app.dependency_overrides[get_app_settings] = lambda: settings
    app.dependency_overrides[get_llm_provider] = lambda: provider
    app.dependency_overrides[get_app_session] = session_dependency(session_factory)
    return app


class RuntimeServices:
    def __init__(
        self,
        *,
        scheduler: SchedulerService,
        bot: TelegramBotService,
        collector: TelegramCollectorService,
        collector_task: asyncio.Task[None] | None,
    ) -> None:
        self.scheduler = scheduler
        self.bot = bot
        self.collector = collector
        self.collector_task = collector_task

    async def stop(self) -> None:
        await self.scheduler.shutdown()
        await self.bot.stop()
        await self.collector.stop()
        if self.collector_task:
            self.collector_task.cancel()
            try:
                await self.collector_task
            except asyncio.CancelledError:
                pass


async def _start_runtime(
    settings: Settings,
    engine: AsyncEngine,
    session_factory: async_sessionmaker[AsyncSession],
    provider: LLMProvider,
) -> RuntimeServices:
    if settings.auto_create_schema:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    scheduler = SchedulerService(
        settings=settings,
        session_factory=session_factory,
        provider=provider,
    )
    bot = TelegramBotService(
        settings=settings,
        session_factory=session_factory,
        provider=provider,
    )
    collector = TelegramCollectorService(settings=settings, session_factory=session_factory)

    scheduler.start()
    await bot.start()
    collector_task: asyncio.Task[None] | None = None
    if settings.telegram_collection_enabled:
        collector_task = asyncio.create_task(collector.start(), name="telegram-collector")

    logger.info(
        "application_started",
        telegram_collection=settings.telegram_collection_enabled,
        telegram_bot=settings.telegram_bot_enabled,
        real_gemini=settings.real_gemini_enabled,
    )
    return RuntimeServices(
        scheduler=scheduler,
        bot=bot,
        collector=collector,
        collector_task=collector_task,
    )
