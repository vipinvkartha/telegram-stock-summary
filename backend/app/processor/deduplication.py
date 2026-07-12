from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

from app.processor.normalization import content_hash, normalize_text


class TextMessage(Protocol):
    id: int
    text: str
    forwarded_from: str | None


@dataclass(frozen=True)
class DedupedMessages:
    kept: list[TextMessage]
    duplicate_ids: set[int]


def is_near_duplicate(left: str, right: str, *, threshold: float = 0.94) -> bool:
    if not left or not right:
        return False
    return SequenceMatcher(None, left.lower(), right.lower()).ratio() >= threshold


def deduplicate_messages(messages: list[TextMessage]) -> DedupedMessages:
    seen_hashes: set[str] = set()
    normalized_texts: list[str] = []
    kept: list[TextMessage] = []
    duplicate_ids: set[int] = set()

    for message in messages:
        normalized = normalize_text(message.text)
        digest = content_hash(normalized)
        if digest in seen_hashes:
            duplicate_ids.add(message.id)
            continue

        if any(is_near_duplicate(normalized, existing) for existing in normalized_texts):
            duplicate_ids.add(message.id)
            continue

        seen_hashes.add(digest)
        normalized_texts.append(normalized)
        kept.append(message)

    return DedupedMessages(kept=kept, duplicate_ids=duplicate_ids)
