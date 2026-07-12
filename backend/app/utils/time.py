from datetime import UTC, datetime


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_hhmm(value: str) -> tuple[int, int]:
    hour, sep, minute = value.partition(":")
    if sep != ":" or not hour.isdigit() or not minute.isdigit():
        raise ValueError(f"Invalid HH:MM value: {value}")
    parsed = (int(hour), int(minute))
    if not (0 <= parsed[0] <= 23 and 0 <= parsed[1] <= 59):
        raise ValueError(f"Invalid HH:MM value: {value}")
    return parsed
