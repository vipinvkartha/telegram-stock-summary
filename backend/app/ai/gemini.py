import asyncio
import time
from typing import Any

import structlog
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.ai.json_utils import parse_json_model
from app.ai.prompts import build_analysis_prompt, build_summarization_prompt
from app.ai.provider import AnalysisResult, LLMProvider, SummaryResult
from app.config import Settings
from app.processor import MessageCluster

logger = structlog.get_logger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self, settings: Settings) -> None:
        self.model = settings.gemini_model
        self.timeout_seconds = settings.ai_request_timeout_seconds
        self._client = self._build_client(settings.gemini_api_key)

    @staticmethod
    def _build_client(api_key: str | None) -> Any:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("Install google-genai to use GeminiProvider") from exc
        return genai.Client(api_key=api_key)

    async def summarize(self, cluster: MessageCluster) -> SummaryResult:
        prompt = build_summarization_prompt(cluster)
        text = await self._generate(prompt, operation="summarize", ticker=cluster.ticker)
        try:
            return parse_json_model(text, SummaryResult)
        except ValueError:
            logger.warning(
                "gemini_invalid_summary_json",
                ticker=cluster.ticker,
                response_length=len(text),
            )
            return _fallback_summary(cluster)

    async def analyze(self, summary: SummaryResult) -> AnalysisResult:
        prompt = build_analysis_prompt(summary)
        text = await self._generate(prompt, operation="analyze", ticker=summary.ticker)
        try:
            return parse_json_model(text, AnalysisResult)
        except ValueError:
            logger.warning(
                "gemini_invalid_analysis_json",
                ticker=summary.ticker,
                response_length=len(text),
            )
            return _fallback_analysis(summary)

    @retry(
        retry=retry_if_exception_type((TimeoutError, RuntimeError, ValueError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def _generate(self, prompt: str, *, operation: str, ticker: str) -> str:
        start = time.perf_counter()
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                ),
                timeout=self.timeout_seconds,
            )
        except Exception as exc:
            logger.exception("gemini_request_failed", operation=operation, ticker=ticker)
            raise RuntimeError("Gemini request failed") from exc

        elapsed_ms = round((time.perf_counter() - start) * 1000)
        text = getattr(response, "text", None)
        usage = getattr(response, "usage_metadata", None)
        logger.info(
            "gemini_request_completed",
            operation=operation,
            ticker=ticker,
            elapsed_ms=elapsed_ms,
            usage=str(usage) if usage else None,
        )
        if not text:
            raise ValueError("Gemini response did not include text")
        return text


def _fallback_summary(cluster: MessageCluster) -> SummaryResult:
    message_count = len(cluster.messages)
    sample = " ".join(message.normalized_text for message in cluster.messages[:3])
    sample = sample[:700].strip()
    summary = (
        f"Telegram discussion mentioned {cluster.ticker} in {message_count} message"
        f"{'' if message_count == 1 else 's'}."
    )
    if sample:
        summary += f" Sample discussion: {sample}"
    return SummaryResult(
        ticker=cluster.ticker,
        summary=summary,
        important_news=[],
        bull_points=[],
        bear_points=[],
        confidence=0.25,
    )


def _fallback_analysis(summary: SummaryResult) -> AnalysisResult:
    return AnalysisResult(
        ticker=summary.ticker,
        overall_sentiment="Neutral",
        short_term_outlook="Insufficient structured evidence for a directional short-term view.",
        medium_term_outlook="Insufficient structured evidence for a directional medium-term view.",
        bull_case=summary.bull_points,
        bear_case=summary.bear_points,
        key_risks=["AI analysis fallback was used because the model returned invalid JSON."],
        confidence=min(summary.confidence, 0.25),
        recommendation="Review the source Telegram messages before taking action.",
        disclaimer="Not financial advice.",
    )
