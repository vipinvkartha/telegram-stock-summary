from collections import Counter

from app.ai.provider import AnalysisResult, LLMProvider, SummaryResult
from app.processor import MessageCluster

POSITIVE_WORDS = {"beat", "beats", "growth", "upgrade", "buy", "bull", "bullish", "breakout"}
NEGATIVE_WORDS = {"miss", "misses", "downgrade", "sell", "bear", "bearish", "risk", "lawsuit"}


class MockLLMProvider(LLMProvider):
    async def summarize(self, cluster: MessageCluster) -> SummaryResult:
        snippets = [message.normalized_text for message in cluster.messages[:5]]
        joined = " ".join(snippets)
        summary = joined[:700] + ("..." if len(joined) > 700 else "")
        bull_points, bear_points = _split_points(snippets)
        return SummaryResult(
            ticker=cluster.ticker,
            summary=summary or f"No substantive discussion found for {cluster.ticker}.",
            important_news=_important_lines(snippets),
            bull_points=bull_points,
            bear_points=bear_points,
            confidence=min(0.95, 0.45 + len(cluster.messages) * 0.08),
        )

    async def analyze(self, summary: SummaryResult) -> AnalysisResult:
        text = " ".join([summary.summary, *summary.bull_points, *summary.bear_points]).lower()
        positive = sum(text.count(word) for word in POSITIVE_WORDS)
        negative = sum(text.count(word) for word in NEGATIVE_WORDS)
        sentiment = "Mixed"
        if positive > negative + 1:
            sentiment = "Bullish"
        elif negative > positive + 1:
            sentiment = "Bearish"
        elif positive == negative == 0:
            sentiment = "Neutral"

        return AnalysisResult(
            ticker=summary.ticker,
            overall_sentiment=sentiment,
            short_term_outlook="Discussion-driven momentum is the main short-term signal.",
            medium_term_outlook=(
                "Medium-term view needs confirmation from fundamentals and price action."
            ),
            bull_case=summary.bull_points,
            bear_case=summary.bear_points,
            key_risks=summary.bear_points[:3]
            or ["Telegram discussions may be incomplete or biased."],
            confidence=round(min(8.5, max(3.0, summary.confidence * 10)), 1),
            recommendation="Watch for verified catalysts before acting.",
            disclaimer="Not financial advice.",
        )


def _split_points(snippets: list[str]) -> tuple[list[str], list[str]]:
    bull: list[str] = []
    bear: list[str] = []
    for snippet in snippets:
        lower = snippet.lower()
        if any(word in lower for word in POSITIVE_WORDS):
            bull.append(snippet[:180])
        if any(word in lower for word in NEGATIVE_WORDS):
            bear.append(snippet[:180])
    return bull[:5], bear[:5]


def _important_lines(snippets: list[str]) -> list[str]:
    keywords = Counter()
    selected: list[str] = []
    for snippet in snippets:
        lower = snippet.lower()
        if any(word in lower for word in {"earnings", "guidance", "upgrade", "downgrade", "sec"}):
            selected.append(snippet[:180])
            keywords.update(lower.split())
    return selected[:5]
