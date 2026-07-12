import logging
import re
import sys
from collections.abc import Mapping
from typing import Any

import structlog

_TELEGRAM_BOT_URL_PATTERN = re.compile(r"(api\.telegram\.org/bot)[^/\s\"]+")


class _RedactTelegramBotTokenFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = _TELEGRAM_BOT_URL_PATTERN.sub(r"\1<redacted>", message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(log_level: str = "INFO") -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
    redaction_filter = _RedactTelegramBotTokenFilter()
    root_logger = logging.getLogger()
    root_logger.addFilter(redaction_filter)
    for handler in root_logger.handlers:
        handler.addFilter(redaction_filter)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_log_context(**kwargs: Any) -> None:
    structlog.contextvars.bind_contextvars(**kwargs)


def event_dict(message: str, **kwargs: Any) -> Mapping[str, Any]:
    return {"event": message, **kwargs}
