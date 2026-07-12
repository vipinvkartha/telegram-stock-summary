from app.ai.json_utils import parse_json_model
from app.ai.provider import SummaryResult


def test_parse_json_model_extracts_object_from_extra_text() -> None:
    result = parse_json_model(
        'Here is the result:\n{"ticker":"NIFTY","summary":"ok","confidence":0.5}\nDone.',
        SummaryResult,
    )

    assert result.ticker == "NIFTY"
    assert result.summary == "ok"


def test_parse_json_model_extracts_fenced_json() -> None:
    result = parse_json_model(
        '```json\n{"ticker":"SBIN","summary":"ok","important_news":[],"confidence":0.7}\n```',
        SummaryResult,
    )

    assert result.ticker == "SBIN"
    assert result.confidence == 0.7
