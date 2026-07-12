from datetime import UTC, date, datetime

from app.ai.prompts import build_analysis_prompt, build_summarization_prompt
from app.ai.provider import SummaryResult
from app.processor.pipeline_types import MessageCluster, ProcessedMessage


def test_summarization_prompt_contains_contract() -> None:
    cluster = MessageCluster(
        ticker="NVDA",
        cluster_date=date(2026, 7, 8),
        messages=[
            ProcessedMessage(
                id=1,
                channel_id=1,
                timestamp=datetime(2026, 7, 8, tzinfo=UTC),
                text="NVIDIA guidance discussion",
                normalized_text="NVIDIA guidance discussion",
                links=[],
                mentions=[],
            )
        ],
    )

    prompt = build_summarization_prompt(cluster)

    assert "Do not invent facts" in prompt
    assert '"ticker": "NVDA"' in prompt
    assert "valid JSON only" in prompt


def test_analysis_prompt_requires_disclaimer() -> None:
    prompt = build_analysis_prompt(SummaryResult(ticker="TSLA", summary="Mixed debate."))

    assert "Not financial advice." in prompt
    assert '"overall_sentiment"' in prompt
