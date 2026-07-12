import json

from app.ai.provider import SummaryResult
from app.processor import MessageCluster


def build_summarization_prompt(cluster: MessageCluster) -> str:
    messages = [
        {
            "id": message.id,
            "timestamp": message.timestamp.isoformat(),
            "text": message.normalized_text,
            "links": message.links,
        }
        for message in cluster.messages
    ]

    payload = {
        "ticker": cluster.ticker,
        "cluster_date": cluster.cluster_date.isoformat(),
        "messages": messages,
    }

    return (
        "You are an equity-market discussion summarizer. Summarize the Telegram "
        "messages for the requested ticker.\n\n"
        "Rules:\n"
        "- Return valid JSON only.\n"
        "- Do not invent facts.\n"
        "- Ignore duplicate messages.\n"
        "- Mention conflicting opinions.\n"
        "- Maximum 300 words in the summary field.\n"
        "- Use empty arrays when no evidence exists.\n\n"
        "Output schema:\n"
        "{\n"
        '  "ticker": "NVDA",\n'
        '  "summary": "...",\n'
        '  "important_news": [],\n'
        '  "bull_points": [],\n'
        '  "bear_points": [],\n'
        '  "confidence": 0.89\n'
        "}\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )


def build_analysis_prompt(summary: SummaryResult) -> str:
    payload = summary.model_dump()
    return (
        "You are an investment analyst. Generate a balanced analysis from the "
        "provided discussion summary.\n\n"
        "Rules:\n"
        "- Return valid JSON only.\n"
        "- Do not invent market data, prices, filings, or earnings results.\n"
        "- Separate bull case, bear case, and risks.\n"
        "- Include the exact disclaimer: Not financial advice.\n\n"
        "Output schema:\n"
        "{\n"
        '  "ticker": "NVDA",\n'
        '  "overall_sentiment": "Bullish",\n'
        '  "short_term_outlook": "...",\n'
        '  "medium_term_outlook": "...",\n'
        '  "bull_case": [],\n'
        '  "bear_case": [],\n'
        '  "key_risks": [],\n'
        '  "confidence": 8.2,\n'
        '  "recommendation": "...",\n'
        '  "disclaimer": "Not financial advice."\n'
        "}\n\n"
        f"Input:\n{json.dumps(payload, ensure_ascii=False)}"
    )
