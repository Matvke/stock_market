import asyncio
from typing import Callable
from services.orderbook import OrderBook
from sqlalchemy.ext.asyncio import AsyncSession
from dao.dao import InstrumentDAO, OrderDAO, TransactionDAO, BalanceDAO
from misc.internal_classes import TradeExecution
from schemas.create import TransactionCreate
from schemas.response import L2OrderBook, Level
from misc.db_models import Order, Instrument
from collections import defaultdict
import logging


class MatchingEngine: 
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


    async def get_orderbook(self, ticker, limit: int) -> L2OrderBook:
        async with self.lock:
            book = self.books.get(ticker)
            if not book: 
                return []
            bid_map = defaultdict(int)
            for order in book.bids:
                if len(bid_map) >= limit: 
                    break
                bid_map[order.price] += order.remaining

            ask_map = defaultdict(int)
            for order in book.asks:
                if len(ask_map) >= limit: 
                    break
                ask_map[order.price] += order.remaining

            return L2OrderBook(
                bid_levels=[Level(price=price, qty=qty) for price, qty in bid_map.items()],
                ask_levels=[Level(price=price, qty=qty) for price, qty in ask_map.items()]
            )


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
            logging.info(msg=f"Added new order {order.ticker, order.direction, order.price, order.qty, order.order_type}")
            return executions
            
    
    def cancel_order(self, cancel_order: Order) -> bool:
        book = self.books.get(cancel_order.ticker)
        if not book:
            return False
        return book.cancel_order(cancel_order)


    def add_instrument(self, instrument: Instrument):
        self.books[instrument.ticker] = OrderBook(instrument.ticker)
        logging.info(f"Added new instrument by the administrator {instrument.ticker}")


    def remove_orderbook(self, ticker: str):
        if ticker in self.books: 
            del self.books[ticker]
            logging.info(f"Deleted orderbook {ticker}")


    async def startup(self, session: AsyncSession):
        async with self.lock:
            async with session.begin_nested():
                instruments = await InstrumentDAO.find_all(session)
                for instrument in instruments:
                    book = OrderBook(instrument.ticker)
                    orders = await OrderDAO.get_open_orders(session, instrument.ticker)
                    book.load_orderbook(orders)
                    self.books[instrument.ticker] = book
            logging.info(msg=f"Startup complete. Orderbooks: {self.books.keys()}")


    async def match_all(self, session: AsyncSession):
        async with self.lock:
            books = dict((t, b) for t,b in self.books.items() if b.has_activity)

        for ticker, book in books.items():
            try:
                async with session.begin_nested():
                    executions: list[TradeExecution] = book.matching_orders()
                    if executions: 
                        logging.info(msg=f"Start execution orders in orderbook {ticker}")
                        await self._process_executions(session, executions)
                        logging.info(msg=f"Executed orders in orderbook {ticker}")
            except Exception as e:
                print(f"Matching error for {ticker}: {e}")
                continue


    async def _process_executions(self, session: AsyncSession, executions: list[TradeExecution]):
        sorted_executions = sorted(executions, key=lambda x: (x.bid_order.user_id, x.ask_order.user_id))
        for execution in sorted_executions:
            # 1. Производим транзакцию перевода токенов 
            # (из зарезервированных в ask ордере единиц)
            await BalanceDAO.upsert_balance(
                session, 
                user_id=execution.bid_order.user_id,
                ticker=execution.bid_order.ticker,
                amount=execution.executed_qty
            )
            # 2. Производим транзакцию перевода рублей
            # (из зарезервированных в bid ордере единиц)

            await BalanceDAO.upsert_balance(
                session, 
                user_id=execution.ask_order.user_id,
                ticker="RUB",
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
                await BalanceDAO.upsert_balance(
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
        try:
            async with session_factory() as session:
                try:
                    async with session.begin():
                        await engine.match_all(session)
                except Exception as match_err:
                    logging.exception(f"Error during order matching: {match_err}")
        except Exception as session_err:
            logging.exception(f"Error creating session: {session_err}")

        await asyncio.sleep(engine.interval)