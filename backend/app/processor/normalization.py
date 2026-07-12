import hashlib
import re
import unicodedata

URL_RE = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")


def extract_urls(text: str) -> list[str]:
    return URL_RE.findall(text or "")


def remove_emoji(text: str) -> str:
    return "".join(ch for ch in text if unicodedata.category(ch) != "So")


def normalize_text(text: str, *, strip_emoji: bool = False) -> str:
    normalized = unicodedata.normalize("NFKC", text or "")
    if strip_emoji:
        normalized = remove_emoji(normalized)
    normalized = URL_RE.sub(" ", normalized)
    normalized = WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def content_hash(text: str) -> str:
    return hashlib.sha256(normalize_text(text).lower().encode("utf-8")).hexdigest()
