from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str


class StockResponse(BaseModel):
    id: int
    ticker: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    id: int
    report_date: datetime
    report_type: str
    title: str
    body: str
    payload: dict[str, Any]

    model_config = {"from_attributes": True}


class GenerateReportRequest(BaseModel):
    hours_back: int = Field(default=12, ge=1, le=168)
    report_type: str = "manual"


class BackfillRequest(BaseModel):
    limit_per_channel: int = Field(default=100, ge=1, le=1000)


class BackfillChannelResponse(BaseModel):
    channel: str
    seen: int
    stored: int
    skipped: int


class BackfillResponse(BaseModel):
    channels: list[BackfillChannelResponse]
    total_seen: int
    total_stored: int
    message: str


class ExtractionDiagnosticsResponse(BaseModel):
    messages_checked: int
    messages_with_mentions: int
    mention_counts: dict[str, int]
    cluster_count: int


class WatchlistResponse(BaseModel):
    stocks: list[StockResponse]
