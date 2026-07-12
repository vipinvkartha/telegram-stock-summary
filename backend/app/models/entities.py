from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database.base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class Channel(Base, TimestampMixin):
    __tablename__ = "channels"
    __table_args__ = (
        UniqueConstraint("telegram_channel_id", name="uq_channels_telegram_channel_id"),
        UniqueConstraint("username", name="uq_channels_username"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_channel_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    messages: Mapped[list["Message"]] = relationship(back_populates="channel")


class Message(Base, TimestampMixin):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("channel_id", "telegram_message_id", name="uq_messages_channel_message"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(
        ForeignKey("channels.id", ondelete="CASCADE"), index=True
    )
    telegram_message_id: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    normalized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    media_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    links: Mapped[list[str]] = mapped_column(JSONType, default=list)
    forwarded_from: Mapped[str | None] = mapped_column(String(255), nullable=True)

    channel: Mapped["Channel"] = relationship(back_populates="messages")
    stock_mappings: Mapped[list["MessageStockMapping"]] = relationship(back_populates="message")


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"
    __table_args__ = (UniqueConstraint("ticker", name="uq_stocks_ticker"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16), index=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(128), nullable=True)

    message_mappings: Mapped[list["MessageStockMapping"]] = relationship(back_populates="stock")
    summaries: Mapped[list["Summary"]] = relationship(back_populates="stock")
    analyses: Mapped[list["Analysis"]] = relationship(back_populates="stock")


class MessageStockMapping(Base):
    __tablename__ = "message_stock_mapping"
    __table_args__ = (UniqueConstraint("message_id", "stock_id", name="uq_message_stock_mapping"),)

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True
    )
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), primary_key=True
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    message: Mapped["Message"] = relationship(back_populates="stock_mappings")
    stock: Mapped["Stock"] = relationship(back_populates="message_mappings")


class Summary(Base, TimestampMixin):
    __tablename__ = "summaries"
    __table_args__ = (UniqueConstraint("stock_id", "report_date", name="uq_summaries_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    summary: Mapped[str] = mapped_column(Text)
    important_news: Mapped[list[str]] = mapped_column(JSONType, default=list)
    bull_points: Mapped[list[str]] = mapped_column(JSONType, default=list)
    bear_points: Mapped[list[str]] = mapped_column(JSONType, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    stock: Mapped["Stock"] = relationship(back_populates="summaries")


class Analysis(Base, TimestampMixin):
    __tablename__ = "analyses"
    __table_args__ = (UniqueConstraint("stock_id", "report_date", name="uq_analyses_stock_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"), index=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sentiment: Mapped[str] = mapped_column(String(80))
    short_term_outlook: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_term_outlook: Mapped[str | None] = mapped_column(Text, nullable=True)
    bull_points: Mapped[list[str]] = mapped_column(JSONType, default=list)
    bear_points: Mapped[list[str]] = mapped_column(JSONType, default=list)
    risks: Mapped[list[str]] = mapped_column(JSONType, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclaimer: Mapped[str] = mapped_column(String(255), default="Not financial advice.")

    stock: Mapped["Stock"] = relationship(back_populates="analyses")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    watchlists: Mapped[list["Watchlist"]] = relationship(back_populates="user")


class Watchlist(Base, TimestampMixin):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), default="Default")

    user: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[list["WatchlistItem"]] = relationship(back_populates="watchlist")


class WatchlistItem(Base, TimestampMixin):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "stock_id", name="uq_watchlist_stock"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id", ondelete="CASCADE"))
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id", ondelete="CASCADE"))

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    stock: Mapped["Stock"] = relationship()


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    report_type: Mapped[str] = mapped_column(String(80), default="scheduled")
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType, default=dict)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
