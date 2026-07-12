from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.processor.entity_extraction import StockMention


class ProcessedMessage(BaseModel):
    id: int
    channel_id: int
    timestamp: datetime
    text: str
    normalized_text: str
    links: list[str] = Field(default_factory=list)
    mentions: list[StockMention] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class MessageCluster(BaseModel):
    ticker: str
    cluster_date: date
    messages: list[ProcessedMessage]
    importance_score: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)
