from typing import Protocol

from app.processor.clustering import cluster_by_stock_and_date
from app.processor.deduplication import deduplicate_messages
from app.processor.entity_extraction import extract_stock_mentions
from app.processor.normalization import extract_urls, normalize_text
from app.processor.pipeline_types import MessageCluster, ProcessedMessage
from app.processor.ranking import rank_clusters


class RawMessage(Protocol):
    id: int
    channel_id: int
    timestamp: object
    text: str
    links: list[str]
    forwarded_from: str | None


class ProcessingPipeline:
    def __init__(self, *, strip_emoji: bool = False) -> None:
        self.strip_emoji = strip_emoji

    def process(self, messages: list[RawMessage]) -> list[MessageCluster]:
        deduped = deduplicate_messages(messages)
        processed: list[ProcessedMessage] = []

        for message in deduped.kept:
            normalized = normalize_text(message.text, strip_emoji=self.strip_emoji)
            mentions = extract_stock_mentions(normalized)
            if not mentions:
                continue
            links = list(message.links or []) or extract_urls(message.text)
            processed.append(
                ProcessedMessage(
                    id=message.id,
                    channel_id=message.channel_id,
                    timestamp=message.timestamp,  # type: ignore[arg-type]
                    text=message.text,
                    normalized_text=normalized,
                    links=links,
                    mentions=mentions,
                )
            )

        return rank_clusters(cluster_by_stock_and_date(processed))


__all__ = ["MessageCluster", "ProcessedMessage", "ProcessingPipeline"]
