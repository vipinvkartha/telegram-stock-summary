from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Stock, User, Watchlist, WatchlistItem
from app.repositories.stocks import StockRepository


class WatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.stocks = StockRepository(session)

    async def get_or_create_user(
        self,
        *,
        telegram_user_id: int | None = None,
        username: str | None = None,
        first_name: str | None = None,
    ) -> User:
        query = select(User)
        if telegram_user_id is not None:
            query = query.where(User.telegram_user_id == telegram_user_id)
        else:
            query = query.where(User.telegram_user_id.is_(None), User.username == username)
        user = (await self.session.scalars(query)).first()
        if user:
            user.username = username or user.username
            user.first_name = first_name or user.first_name
            return user
        user = User(telegram_user_id=telegram_user_id, username=username, first_name=first_name)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_or_create_default(self, user: User | None = None) -> Watchlist:
        query = select(Watchlist).where(Watchlist.name == "Default")
        if user:
            query = query.where(Watchlist.user_id == user.id)
        else:
            query = query.where(Watchlist.user_id.is_(None))
        watchlist = (await self.session.scalars(query)).first()
        if watchlist:
            return watchlist
        watchlist = Watchlist(user_id=user.id if user else None, name="Default")
        self.session.add(watchlist)
        await self.session.flush()
        return watchlist

    async def list_default(self, user: User | None = None) -> list[Stock]:
        watchlist = await self.get_or_create_default(user)
        query = (
            select(Watchlist)
            .where(Watchlist.id == watchlist.id)
            .options(selectinload(Watchlist.items).selectinload(WatchlistItem.stock))
        )
        loaded = (await self.session.scalars(query)).one()
        return [item.stock for item in loaded.items]

    async def add_ticker(self, ticker: str, user: User | None = None) -> Stock:
        stock = await self.stocks.get_or_create(ticker)
        watchlist = await self.get_or_create_default(user)
        existing = await self.session.scalar(
            select(WatchlistItem.id).where(
                WatchlistItem.watchlist_id == watchlist.id,
                WatchlistItem.stock_id == stock.id,
            )
        )
        if not existing:
            self.session.add(WatchlistItem(watchlist_id=watchlist.id, stock_id=stock.id))
            await self.session.flush()
        return stock

    async def remove_ticker(self, ticker: str, user: User | None = None) -> bool:
        watchlist = await self.get_or_create_default(user)
        stock = await self.stocks.get_by_ticker(ticker)
        if not stock:
            return False
        item = await self.session.scalar(
            select(WatchlistItem).where(
                WatchlistItem.watchlist_id == watchlist.id,
                WatchlistItem.stock_id == stock.id,
            )
        )
        if not item:
            return False
        await self.session.delete(item)
        return True
