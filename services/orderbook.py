from sortedcontainers import SortedList
from misc.enums import DirectionEnum, StatusEnum
from misc.internal_classes import InternalOrder, TradeExecution
from misc.db_models import Order
import logging


class OrderBook():
    def __init__(self, ticker: str):
        self.ticker = ticker
        self.bids: SortedList[InternalOrder] = SortedList(key=lambda order: (-order.price, order.timestamp)) # Покупание
        self.asks: SortedList[InternalOrder] = SortedList(key=lambda order: (order.price, order.timestamp)) # Продавание
        self.has_activity = False
    

    def cancel_order(self, cancel_order: Order) -> bool:
        self.has_activity = True
        for order in self.asks:
            if cancel_order.id == order.id:
                self.asks.discard(order)
                return True
        
        for order in self.bids:
            if cancel_order.id == order.id:
                self.bids.discard(order)
                return True
            
        return False
    

    def add_limit_order(self, new_order: Order):
        self.has_activity = True
        if new_order.direction == DirectionEnum.BUY:
            self.bids.add(InternalOrder.from_db(new_order))
        else:
            self.asks.add(InternalOrder.from_db(new_order))

        return []


    def add_market_order(self, new_order: Order, balance: int) -> list[TradeExecution]:
        self.has_activity = True
        order = InternalOrder.from_db(new_order)
        if self._can_execute_market_order(order, balance):
            return self._execute_market_order(order)

        return []


    def _can_execute_market_order(self, new_order: InternalOrder, balance: int):
        book: SortedList[InternalOrder] = self.asks if new_order.direction == DirectionEnum.BUY else self.bids
        total_cost = 0 # сколько РУБЛЕЙ потратим или получим
        available_qty = 0 # сколько токенов доступно в стакане
        remaining_qty = new_order.qty

        for order in book:
            if remaining_qty <= 0:
                break

            trade_qty = min(order.remaining, remaining_qty)
            available_qty += trade_qty
            total_cost += trade_qty * order.price
            remaining_qty -= trade_qty

        # Недостаточно ордеров на нужное кол-во
        if available_qty < new_order.qty:
            logging.info("Not enough offers. Market order denied")
            return False

        if new_order.direction == DirectionEnum.BUY:
            # Нужно достаточно РУБЛЕЙ, чтобы купить
            if balance < total_cost:
                logging.info("Not enough balance. Market order denied")
                return False
        else: 
            # Нужно достаточно самих токенов
            if balance < new_order.qty:
                logging.info("Not enough balance. Market order denied")
                return False

        return True


    def _execute_market_order(self, new_order: InternalOrder) -> list[TradeExecution]:
        trades = []
        book = self.asks if new_order.direction == DirectionEnum.BUY else self.bids
        
        for existed_order in book:
            if new_order.status == StatusEnum.EXECUTED:
                break

            # Определяем bid и ask в зависимости от направления ордера
            if new_order.direction == DirectionEnum.BUY:
                bid, ask = new_order, existed_order
            else:
                bid, ask = existed_order, new_order

            trade = self._execute_trade(bid=bid, ask=ask)
            trades.append(trade)

            if existed_order.status == StatusEnum.EXECUTED:
                book.remove(existed_order)

        return trades


    def matching_orders(self) -> list[TradeExecution]:
        trades: list[TradeExecution] = []

        while self.bids and self.asks and self.bids[0].price >= self.asks[0].price:
            bid: InternalOrder = self.bids[0] # Покупание
            ask: InternalOrder = self.asks[0] # Продавание

            trade = self._execute_trade(bid=bid, ask=ask)
            trades.append(trade)

            if bid.status == StatusEnum.EXECUTED:
                self.bids.pop(0)

            if ask.status == StatusEnum.EXECUTED:
                self.asks.pop(0)

        self.has_activity = False

        return trades


    def _execute_trade(self, bid: InternalOrder, ask: InternalOrder) -> tuple:
        # Колво исполненных активов
        executed_qty = min(bid.qty - bid.filled, ask.qty - ask.filled)
        execution_price = ask.price if ask.price else bid.price

        # Расчет сдачи
        bid_order_change = None
        if bid.price is not None and bid.price > execution_price:
            bid_order_change = (bid.price - execution_price) * executed_qty

        # Обновляем остатки
        bid.filled += executed_qty
        ask.filled += executed_qty

        self._update_status(bid)
        self._update_status(ask)

        return TradeExecution(
                    bid_order=bid,
                    ask_order=ask,
                    executed_qty=executed_qty,
                    execution_price=execution_price,
                    bid_order_change=bid_order_change
                )


    def _update_status(self, order:InternalOrder):
        if order.filled == order.qty:
            order.status = StatusEnum.EXECUTED
        else: 
            order.status = StatusEnum.PARTIALLY_EXECUTED


    def load_orderbook(self, orders: list[Order]):
        for order in orders:
            internal = InternalOrder.from_db(order)
            if internal.direction == DirectionEnum.BUY:
                self.bids.add(internal)
            else:
                self.asks.add(internal)

    
    def get_bids(self) -> SortedList[InternalOrder]:
        return self.bids
    

    def get_asks(self) -> SortedList[InternalOrder]:
        return self.asks
        

