from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import LLMProvider
from app.config import Settings
from app.models import Report
from app.services import ReportService
from app.utils.time import parse_hhmm

logger = structlog.get_logger(__name__)


class SchedulerService:
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
        self.timezone = ZoneInfo(settings.report_timezone)
        self.scheduler = AsyncIOScheduler(timezone=self.timezone)

    def start(self) -> None:
        for report_time in self.settings.report_times:
            hour, minute = parse_hhmm(report_time)
            self.scheduler.add_job(
                self.generate_scheduled_report,
                CronTrigger(hour=hour, minute=minute, timezone=self.timezone),
                id=f"report-{report_time}",
                replace_existing=True,
            )
        self.scheduler.add_job(
            self.archive_old_reports,
            CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=self.timezone),
            id="archive-old-reports",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("scheduler_started", report_times=self.settings.report_times)

    async def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("scheduler_stopped")

    async def generate_scheduled_report(self) -> None:
        until = datetime.now(UTC)
        since = until - timedelta(hours=self.settings.default_report_hours)
        async with self.session_factory() as session:
            service = ReportService(session, self.provider, self.settings)
            try:
                await service.generate(since=since, until=until, report_type="scheduled")
            except Exception:
                logger.exception("scheduled_report_failed")

    async def archive_old_reports(self) -> None:
        cutoff = datetime.now(UTC) - timedelta(days=90)
        async with self.session_factory() as session:
            await session.execute(
                update(Report)
                .where(Report.report_date < cutoff, Report.archived_at.is_(None))
                .values(archived_at=datetime.now(UTC))
            )
            await session.commit()
            logger.info("old_reports_archived", cutoff=cutoff.isoformat())
