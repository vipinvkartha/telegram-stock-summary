from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MessageStockMapping, Stock


class StockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self) -> list[Stock]:
        result = await self.session.scalars(select(Stock).order_by(Stock.ticker.asc()))
        return list(result)

    async def get_by_ticker(self, ticker: str) -> Stock | None:
        result = await self.session.scalars(select(Stock).where(Stock.ticker == ticker.upper()))
        return result.first()

    async def get_or_create(
        self,
        ticker: str,
        *,
        company_name: str | None = None,
        exchange: str | None = None,
        sector: str | None = None,
    ) -> Stock:
        ticker = ticker.upper()
        stock = await self.get_by_ticker(ticker)
        if stock:
            stock.company_name = company_name or stock.company_name
            stock.exchange = exchange or stock.exchange
            stock.sector = sector or stock.sector
            return stock

        stock = Stock(ticker=ticker, company_name=company_name, exchange=exchange, sector=sector)
        self.session.add(stock)
        await self.session.flush()
        return stock

    async def map_message(self, *, message_id: int, stock_id: int, confidence: float) -> None:
        existing = await self.session.get(
            MessageStockMapping,
            {"message_id": message_id, "stock_id": stock_id},
        )
        if existing:
            existing.confidence = max(existing.confidence, confidence)
            return
        self.session.add(
            MessageStockMapping(
                message_id=message_id,
                stock_id=stock_id,
                confidence=confidence,
            )
        )
