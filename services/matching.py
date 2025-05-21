import asyncio
from typing import Callable
from services.orderbook import OrderBook
from sqlalchemy.ext.asyncio import AsyncSession
from dao.dao import InstrumentDAO, OrderDAO
from misc.internal_classes import TradeExecution
from schemas.response import L2OrderBook, Level
from misc.db_models import Order, Instrument
from collections import defaultdict
import logging
from services.trade_execution import trade_executor

class MatchingEngine: 
    def  __init__(self, interval: float = 1.0):
        self.books: dict[str, OrderBook] = {}
        self.interval = interval
        self.lock = asyncio.Lock()
    

    def get_bids_from_book(self, ticker: str):
        book = self.books.get(ticker)
        return book.get_bids() if book else []


    def get_asks_from_book(self, ticker: str):
        book = self.books.get(ticker)
        return book.get_asks() if book else []


    def get_orderbook(self, ticker, limit: int) -> L2OrderBook:
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

        book = L2OrderBook(
            bid_levels=[Level(price=price, qty=qty) for price, qty in bid_map.items()],
            ask_levels=[Level(price=price, qty=qty) for price, qty in ask_map.items()]
        )
        logging.info(f"Orderbook requested. {book}")
        return book


    def add_limit_order(self, order: Order):
        book = self.books.get(order.ticker)
        if not book:
            raise ValueError(f"Order book for ticker '{order.ticker}' not found. Did you forget to call add_instrument or startup?") 
        logging.info(msg=f"Added new order {order.ticker, order.direction, order.price, order.qty, order.order_type}")
        return book.add_limit_order(order)


    def add_market_order(self, order: Order, balance: int):
        book = self.books.get(order.ticker)
        if not book:
            raise ValueError(f"Order book for ticker '{order.ticker}' not found. Did you forget to call add_instrument or startup?") 
        executions: list[TradeExecution] = book.add_market_order(order, balance)
        logging.info(msg=f"Added new order {order.ticker, order.direction, order.price, order.qty, order.order_type}")
        return executions

    
    def cancel_order(self, cancel_order: Order) -> bool:
        book = self.books.get(cancel_order.ticker)
        logging.info(f"Trying cancel order {cancel_order.ticker, cancel_order.direction, cancel_order.price, cancel_order.qty, cancel_order.order_type}")
        if not book:
            logging.info(f"Order cancel error: book {cancel_order.ticker} not exist.")
            return False
        if book.cancel_order(cancel_order):
            logging.info(f"Order canceled {cancel_order.ticker, cancel_order.direction, cancel_order.price, cancel_order.qty, cancel_order.order_type}")
            return True
        logging.info(f"Order cancel error: order {cancel_order.ticker, cancel_order.direction, cancel_order.price, cancel_order.qty, cancel_order.order_type} not found.")
        return False


    def add_instrument(self, instrument: Instrument):
        self.books[instrument.ticker] = OrderBook(instrument.ticker)
        logging.info(f"Added new instrument {instrument.ticker}")


    def remove_orderbook(self, ticker: str):
        if ticker in self.books: 
            del self.books[ticker]
            logging.info(f"Deleted instrument {ticker}")
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
        async with self.lock: # TODO проблемка.
            books = dict((t, b) for t,b in self.books.items() if b.has_activity)

        for ticker, book in books.items():
            try:
                executions: list[TradeExecution] = book.matching_orders()
                if executions: 
                    await trade_executor.execute_trade(session, executions)
                    logging.info(msg=f"Executed orders in orderbook {ticker}")
            except Exception as e:
                print(f"Matching error for {ticker}: {e}")
                continue


async def run_matching_engine(engine: MatchingEngine, session_factory: Callable[[], AsyncSession]):
    while True:
        try:
            async with session_factory() as session:
                try:
                    await engine.match_all(session)
                except Exception as match_err:
                    logging.exception(f"Error during order matching: {match_err}")
        except Exception as session_err:
            logging.exception(f"Error creating session: {session_err}")

        await asyncio.sleep(engine.interval)