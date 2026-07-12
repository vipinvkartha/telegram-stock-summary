from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Stock, User
from app.repositories.watchlists import WatchlistRepository


class WatchlistService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = WatchlistRepository(session)

    async def list_default(self, user: User | None = None) -> list[Stock]:
        return await self.repository.list_default(user)

    async def add(self, ticker: str, user: User | None = None) -> Stock:
        return await self.repository.add_ticker(ticker.upper(), user)

    async def remove(self, ticker: str, user: User | None = None) -> bool:
        return await self.repository.remove_ticker(ticker.upper(), user)
