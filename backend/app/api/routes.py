import secrets
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import LLMProvider
from app.api.dependencies import get_app_session, get_app_settings, get_llm_provider
from app.config import Settings
from app.repositories import StockRepository
from app.schemas import (
    BackfillRequest,
    BackfillResponse,
    ExtractionDiagnosticsResponse,
    GenerateReportRequest,
    HealthResponse,
    ReportResponse,
    StockResponse,
    WatchlistResponse,
)
from app.services import ReportService, WatchlistService
from app.processor import ProcessingPipeline
from app.repositories import MessageRepository

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, environment=settings.environment)


@router.get("/stocks", response_model=list[StockResponse])
async def list_stocks(session: AsyncSession = Depends(get_app_session)) -> list[StockResponse]:
    stocks = await StockRepository(session).list()
    return [StockResponse.model_validate(stock) for stock in stocks]


@router.get("/reports/latest", response_model=ReportResponse)
async def latest_report(
    session: AsyncSession = Depends(get_app_session),
    provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_app_settings),
) -> ReportResponse:
    service = ReportService(session, provider, settings)
    report = await service.latest()
    if not report:
        raise HTTPException(status_code=404, detail="No reports generated yet")
    return ReportResponse.model_validate(report)


@router.post("/reports/generate", response_model=ReportResponse)
async def generate_report(
    request: GenerateReportRequest,
    session: AsyncSession = Depends(get_app_session),
    provider: LLMProvider = Depends(get_llm_provider),
    settings: Settings = Depends(get_app_settings),
) -> ReportResponse:
    until = datetime.now(UTC)
    since = until - timedelta(hours=request.hours_back)
    service = ReportService(session, provider, settings)
    report = await service.generate(since=since, until=until, report_type=request.report_type)
    return ReportResponse.model_validate(report)


@router.post("/telegram/backfill", response_model=BackfillResponse)
async def backfill_telegram(
    request: BackfillRequest,
    app_request: Request,
    settings: Settings = Depends(get_app_settings),
    x_admin_token: str | None = Header(default=None),
) -> BackfillResponse:
    _require_admin_token(settings, x_admin_token)
    collector = app_request.app.state.runtime.collector
    try:
        result = await collector.backfill(limit_per_channel=request.limit_per_channel)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return BackfillResponse.model_validate(result)


@router.get("/telegram/extraction-diagnostics", response_model=ExtractionDiagnosticsResponse)
async def extraction_diagnostics(
    settings: Settings = Depends(get_app_settings),
    session: AsyncSession = Depends(get_app_session),
    x_admin_token: str | None = Header(default=None),
    limit: int = 100,
) -> ExtractionDiagnosticsResponse:
    _require_admin_token(settings, x_admin_token)
    limit = max(1, min(limit, 1000))
    messages = await MessageRepository(session).latest(limit=limit)
    pipeline = ProcessingPipeline(strip_emoji=settings.normalize_remove_emoji)
    clusters = pipeline.process(messages)
    mention_counts: Counter[str] = Counter()
    message_ids_with_mentions: set[int] = set()
    for cluster in clusters:
        mention_counts[cluster.ticker] += len(cluster.messages)
        message_ids_with_mentions.update(message.id for message in cluster.messages)
    return ExtractionDiagnosticsResponse(
        messages_checked=len(messages),
        messages_with_mentions=len(message_ids_with_mentions),
        mention_counts=dict(mention_counts.most_common()),
        cluster_count=len(clusters),
    )


@router.get("/watchlist", response_model=WatchlistResponse)
async def get_watchlist(session: AsyncSession = Depends(get_app_session)) -> WatchlistResponse:
    service = WatchlistService(session)
    stocks = await service.list_default()
    return WatchlistResponse(stocks=[StockResponse.model_validate(stock) for stock in stocks])


def _require_admin_token(settings: Settings, provided_token: str | None) -> None:
    if not settings.admin_api_token:
        raise HTTPException(status_code=503, detail="ADMIN_API_TOKEN is not configured")
    if not provided_token or not secrets.compare_digest(provided_token, settings.admin_api_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")
