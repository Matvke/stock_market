import asyncio
from typing import Callable
from services.orderbook import OrderBook
from sqlalchemy.ext.asyncio import AsyncSession
from dao.dao import InstrumentDAO, OrderDAO, TransactionDAO, BalanceDAO
from misc.internal_classes import InternalOrder, TradeExecution
from schemas.request import BalanceRequest
from schemas.create import TransactionCreate
from misc.db_models import Order, Instrument


class MatchingEngine: # TODO исправить возможность сделки с собой
    def  __init__(self, interval: float = 1.0):
        self.books: dict[str, OrderBook] = {}
        self.interval = interval
        self.lock = asyncio.Lock()
    

    async def get_bids_from_book(self, ticker: str):
        async with self.lock:
            book = self.books.get(ticker)
            return book.get_bids() if book else []


    async def get_asks_from_book(self, ticker: str):
        async with self.lock:
            book = self.books.get(ticker)
            return book.get_asks() if book else []


    async def add_order(self, session: AsyncSession, order: Order):
        """Перед отправкой, требуется списать баланс пользователей. 
        Метод гарантирует полное исполнение или отколнение рыночного ордера."""
        book = self.books.get(order.ticker)
        if not book:
            raise ValueError(f"Order book for ticker '{order.ticker}' not found. Did you forget to call add_instrument or startup?") 
        async with self.lock:
            executions: list[TradeExecution] = book.add_order(order) 
            if executions:
                await self._process_executions(session, executions)
            return executions
            

    async def add_instrument(self, instrument: Instrument):
        self.books[instrument.ticker] = OrderBook(instrument.ticker)


    async def startup(self, session: AsyncSession):
        async with self.lock:
            instruments = await InstrumentDAO.find_all(session)
            for instrument in instruments:
                book = OrderBook(instrument.ticker)
                orders = await OrderDAO.get_open_orders(session, instrument.ticker)
                book.load_orderbook(orders)
                self.books[instrument.ticker] = book


    async def match_all(self, session: AsyncSession):
        async with self.lock:
            for ticker, book in self.books.items():
                try:
                    async with session.begin_nested(): # SAVEPOINT на каждую книгу
                        executions: list[TradeExecution] = book.matching_orders()
                        if executions: 
                            await self._process_executions(session, executions)
                    # Автокоммит если все норм
                except Exception as e:
                    print(f"Matching error for {ticker}: {e}")
                    continue


    async def _process_executions(self, session: AsyncSession, executions: list[TradeExecution]):
        for execution in executions:
            # 1. Производим транзакцию перевода токенов 
            # (из зарезервированных в ask ордере единиц)
            await BalanceDAO.update_balance(
                session, 
                BalanceRequest(
                    user_id=execution.bid_order.user_id,
                    ticker=execution.bid_order.ticker
                ),
                amount=execution.executed_qty
            )
            # 2. Производим транзакцию перевода рублей
            # (из зарезервированных в bid ордере единиц)

            await BalanceDAO.update_balance(
                session, 
                BalanceRequest(
                    user_id=execution.ask_order.user_id,
                    ticker="RUB"
                ),
                amount=execution.executed_qty * execution.execution_price
            )

            # 3. Фиксируем транзакцию перевода токенов
            await TransactionDAO.add(
                session, 
                TransactionCreate(
                    buyer_id=execution.bid_order.user_id,
                    seller_id=execution.ask_order.user_id,
                    ticker=execution.ask_order.ticker,
                    amount=execution.executed_qty,
                    price=execution.execution_price
                )
            )

            # 4. Фиксируем транзакцию перевода рублей
            await TransactionDAO.add(
                session,
                TransactionCreate(
                    buyer_id=execution.ask_order.user_id,
                    seller_id=execution.bid_order.user_id,
                    ticker="RUB",
                    amount=execution.executed_qty * execution.execution_price,
                    price=1
                )
            )

            # 5. Возвращаем сдачу (если есть)
            if execution.bid_order_change:
                await BalanceDAO.add_to_balance(
                    session,
                    user_id=execution.bid_order.user_id,
                    ticker="RUB",
                    amount=execution.bid_order_change
                )
            
            # 6. Обновляем статусы ордеров
            await OrderDAO.update_after_trade(
                session,
                order_id=execution.bid_order.id,
                filled_delta=execution.executed_qty,
                new_status=execution.bid_order.status
            )
            
            await OrderDAO.update_after_trade(
                session,
                order_id=execution.ask_order.id,
                filled_delta=execution.executed_qty,
                new_status=execution.ask_order.status
            )


async def run_matching_engine(engine: MatchingEngine, session_factory: Callable[[], AsyncSession]):
    while True:
        async with session_factory() as session:
            await engine.match_all(session)
        await asyncio.sleep(engine.interval)