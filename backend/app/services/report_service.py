from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import AnalysisResult, LLMProvider, SummaryResult
from app.config import Settings
from app.models import Report
from app.processor import MessageCluster, ProcessingPipeline
from app.repositories import MessageRepository, ReportRepository, StockRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GeneratedStockReport:
    ticker: str
    summary: SummaryResult
    analysis: AnalysisResult
    message_count: int
    importance_score: float


class ReportService:
    def __init__(self, session: AsyncSession, provider: LLMProvider, settings: Settings) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings
        self.messages = MessageRepository(session)
        self.stocks = StockRepository(session)
        self.reports = ReportRepository(session)
        self.pipeline = ProcessingPipeline(strip_emoji=settings.normalize_remove_emoji)

    async def generate(
        self,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
        report_type: str = "manual",
    ) -> Report:
        until = until or datetime.now(UTC)
        since = since or until - timedelta(hours=self.settings.default_report_hours)

        raw_messages = await self.messages.list_between(since=since, until=until)
        clusters = self.pipeline.process(raw_messages)
        clusters = clusters[: self.settings.max_report_stocks]

        logger.info(
            "report_generation_started",
            since=since.isoformat(),
            until=until.isoformat(),
            raw_message_count=len(raw_messages),
            cluster_count=len(clusters),
        )

        if not clusters:
            report = await self._create_empty_report(until=until, report_type=report_type)
            await self.session.commit()
            return report

        stock_reports: list[GeneratedStockReport] = []
        for cluster in clusters:
            trimmed_cluster = _trim_cluster(cluster, self.settings.max_messages_per_stock)
            await self._persist_stock_mappings(trimmed_cluster)
            summary = await self.provider.summarize(trimmed_cluster)
            analysis = await self.provider.analyze(summary)
            stock = await self.stocks.get_or_create(
                summary.ticker,
                company_name=_company_name_for_cluster(trimmed_cluster),
            )
            await self.reports.add_summary(
                stock_id=stock.id,
                report_date=until,
                summary=summary.summary,
                important_news=summary.important_news,
                bull_points=summary.bull_points,
                bear_points=summary.bear_points,
                confidence=summary.confidence,
            )
            await self.reports.add_analysis(
                stock_id=stock.id,
                report_date=until,
                sentiment=analysis.overall_sentiment,
                short_term_outlook=analysis.short_term_outlook,
                medium_term_outlook=analysis.medium_term_outlook,
                bull_points=analysis.bull_case,
                bear_points=analysis.bear_case,
                risks=analysis.key_risks,
                confidence=analysis.confidence,
                recommendation=analysis.recommendation,
                disclaimer=analysis.disclaimer,
            )
            stock_reports.append(
                GeneratedStockReport(
                    ticker=summary.ticker,
                    summary=summary,
                    analysis=analysis,
                    message_count=len(trimmed_cluster.messages),
                    importance_score=trimmed_cluster.importance_score,
                )
            )

        title = _report_title(until)
        body = format_report(title=title, stock_reports=stock_reports)
        payload = {
            "since": since.isoformat(),
            "until": until.isoformat(),
            "most_discussed": [
                {
                    "ticker": item.ticker,
                    "message_count": item.message_count,
                    "importance_score": item.importance_score,
                    "sentiment": item.analysis.overall_sentiment,
                }
                for item in stock_reports
            ],
            "stocks": [
                {
                    "ticker": item.ticker,
                    "summary": item.summary.model_dump(),
                    "analysis": item.analysis.model_dump(),
                    "message_count": item.message_count,
                }
                for item in stock_reports
            ],
        }
        report = await self.reports.create(
            report_date=until,
            report_type=report_type,
            title=title,
            body=body,
            payload=payload,
        )
        await self.session.commit()
        logger.info(
            "report_generation_completed", report_id=report.id, stock_count=len(stock_reports)
        )
        return report

    async def latest(self) -> Report | None:
        return await self.reports.latest()

    async def _create_empty_report(self, *, until: datetime, report_type: str) -> Report:
        title = _report_title(until)
        body = (
            f"{title}\n\n"
            "Overall Market Sentiment: Not enough Telegram discussion data.\n\n"
            "Most Discussed Stocks: None\n\n"
            "Disclaimer: Not financial advice."
        )
        return await self.reports.create(
            report_date=until,
            report_type=report_type,
            title=title,
            body=body,
            payload={"stocks": [], "message": "No qualifying stock discussions found."},
        )

    async def _persist_stock_mappings(self, cluster: MessageCluster) -> None:
        for message in cluster.messages:
            for mention in message.mentions:
                stock = await self.stocks.get_or_create(
                    mention.ticker,
                    company_name=mention.company_name,
                    exchange=mention.exchange,
                    sector=mention.sector,
                )
                await self.stocks.map_message(
                    message_id=message.id,
                    stock_id=stock.id,
                    confidence=mention.confidence,
                )


def format_report(*, title: str, stock_reports: list[GeneratedStockReport]) -> str:
    sentiment_counter = Counter(item.analysis.overall_sentiment for item in stock_reports)
    overall_sentiment = sentiment_counter.most_common(1)[0][0] if stock_reports else "Neutral"
    lines = [
        title,
        "",
        f"Overall Market Sentiment: {overall_sentiment}",
        "",
        "Most Discussed Stocks: "
        + ", ".join(f"{item.ticker} ({item.message_count})" for item in stock_reports),
        "",
        "--------------------------------",
    ]

    all_risks: list[str] = []
    opportunities: list[str] = []
    for item in stock_reports:
        lines.extend(
            [
                "",
                item.ticker,
                "",
                "Summary",
                item.summary.summary,
                "",
                "AI Analysis",
                f"Sentiment: {item.analysis.overall_sentiment}",
                f"Short Term: {item.analysis.short_term_outlook}",
                f"Medium Term: {item.analysis.medium_term_outlook}",
            ]
        )
        if item.analysis.bull_case:
            lines.append("Bull Case: " + "; ".join(item.analysis.bull_case[:3]))
            opportunities.extend(item.analysis.bull_case[:2])
        if item.analysis.bear_case:
            lines.append("Bear Case: " + "; ".join(item.analysis.bear_case[:3]))
        if item.analysis.key_risks:
            lines.append("Key Risks: " + "; ".join(item.analysis.key_risks[:3]))
            all_risks.extend(item.analysis.key_risks[:2])
        if item.analysis.recommendation:
            lines.append("Recommendation: " + item.analysis.recommendation)
        lines.extend(["", "--------------------------------"])

    lines.extend(
        [
            "",
            "Top Risks",
            _format_items(all_risks),
            "",
            "Market Opportunities",
            _format_items(opportunities),
            "",
            "Stocks To Watch",
            ", ".join(item.ticker for item in stock_reports[:5]) or "None",
            "",
            "Disclaimer: Not financial advice.",
        ]
    )
    return "\n".join(lines).strip()


def _trim_cluster(cluster: MessageCluster, max_messages: int) -> MessageCluster:
    return cluster.model_copy(update={"messages": cluster.messages[:max_messages]})


def _company_name_for_cluster(cluster: MessageCluster) -> str | None:
    for message in cluster.messages:
        for mention in message.mentions:
            if mention.ticker == cluster.ticker and mention.company_name:
                return mention.company_name
    return None


def _report_title(moment: datetime) -> str:
    return "Morning Market Summary" if moment.hour < 15 else "Evening Market Summary"


def _format_items(items: list[str]) -> str:
    if not items:
        return "None identified."
    deduped = list(dict.fromkeys(items))
    return "\n".join(f"- {item}" for item in deduped[:8])
