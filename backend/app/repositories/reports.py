from datetime import datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Analysis, Report, Summary


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest(self) -> Report | None:
        query = (
            select(Report).where(Report.archived_at.is_(None)).order_by(desc(Report.report_date))
        )
        return (await self.session.scalars(query.limit(1))).first()

    async def create(
        self,
        *,
        report_date: datetime,
        report_type: str,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> Report:
        report = Report(
            report_date=report_date,
            report_type=report_type,
            title=title,
            body=body,
            payload=payload,
        )
        self.session.add(report)
        await self.session.flush()
        return report

    async def add_summary(
        self,
        *,
        stock_id: int,
        report_date: datetime,
        summary: str,
        important_news: list[str],
        bull_points: list[str],
        bear_points: list[str],
        confidence: float,
    ) -> Summary:
        row = Summary(
            stock_id=stock_id,
            report_date=report_date,
            summary=summary,
            important_news=important_news,
            bull_points=bull_points,
            bear_points=bear_points,
            confidence=confidence,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def add_analysis(
        self,
        *,
        stock_id: int,
        report_date: datetime,
        sentiment: str,
        short_term_outlook: str | None,
        medium_term_outlook: str | None,
        bull_points: list[str],
        bear_points: list[str],
        risks: list[str],
        confidence: float,
        recommendation: str | None,
        disclaimer: str,
    ) -> Analysis:
        row = Analysis(
            stock_id=stock_id,
            report_date=report_date,
            sentiment=sentiment,
            short_term_outlook=short_term_outlook,
            medium_term_outlook=medium_term_outlook,
            bull_points=bull_points,
            bear_points=bear_points,
            risks=risks,
            confidence=confidence,
            recommendation=recommendation,
            disclaimer=disclaimer,
        )
        self.session.add(row)
        await self.session.flush()
        return row
