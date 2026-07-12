from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field

from app.processor import MessageCluster


class SummaryResult(BaseModel):
    ticker: str
    summary: str
    important_news: list[str] = Field(default_factory=list)
    bull_points: list[str] = Field(default_factory=list)
    bear_points: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class AnalysisResult(BaseModel):
    ticker: str
    overall_sentiment: Literal["Bullish", "Bearish", "Neutral", "Mixed"] | str
    short_term_outlook: str
    medium_term_outlook: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    recommendation: str | None = None
    disclaimer: str = "Not financial advice."


class LLMProvider(ABC):
    @abstractmethod
    async def summarize(self, cluster: MessageCluster) -> SummaryResult:
        raise NotImplementedError

    @abstractmethod
    async def analyze(self, summary: SummaryResult) -> AnalysisResult:
        raise NotImplementedError
