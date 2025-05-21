from sortedcontainers import SortedList
from misc.enums import DirectionEnum, StatusEnum
from misc.internal_classes import InternalOrder, TradeExecution
from misc.db_models import Order


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
            return False

        if new_order.direction == DirectionEnum.BUY:
            # Нужно достаточно РУБЛЕЙ, чтобы купить
            if balance < total_cost:
                return False
        else: 
            # Нужно достаточно самих токенов
            if balance < new_order.qty:
                return False

        return True


    def _execute_market_order(self, new_order: InternalOrder) -> list[TradeExecution]:
        if new_order.remaining == 0:
            return []

        executions: list[TradeExecution] = []
        book = self.asks if new_order.direction == DirectionEnum.BUY else self.bids

        for existed_order in list(book):

            if new_order.status == StatusEnum.EXECUTED:
                break

            execution_qty = min(new_order.remaining, existed_order.remaining)
            execution_price = existed_order.price

            # Обновляем остатки
            new_order.filled += execution_qty
            existed_order.filled += execution_qty

            # Удаляем исполненные ордера из стакана
            if existed_order.filled == existed_order.qty:
                existed_order.status = StatusEnum.EXECUTED
                book.remove(existed_order)
            else:
                existed_order.status = StatusEnum.PARTIALLY_EXECUTED

            if new_order.filled == new_order.qty:
                new_order.status = StatusEnum.EXECUTED
            else:
                new_order.status = StatusEnum.PARTIALLY_EXECUTED

            executions.append(TradeExecution(
                bid_order=new_order if new_order.direction == DirectionEnum.BUY else existed_order,
                ask_order=existed_order if new_order.direction == DirectionEnum.BUY else new_order,
                executed_qty=execution_qty,
                execution_price=execution_price,
                bid_order_change=None
            ))

        return executions


    def matching_orders(self) -> list[TradeExecution]:
        trades: list[TradeExecution] = []

        while self.bids and self.asks and self.bids[0].price >= self.asks[0].price:
            bid: InternalOrder = self.bids[0] # Покупание
            ask: InternalOrder = self.asks[0] # Продавание

            # Колво исполненных активов
            executed_qty = min(bid.qty - bid.filled, ask.qty - ask.filled)
            execution_price = ask.price  

            # Расчет сдачи
            bid_order_change = (bid.price - execution_price) * executed_qty if bid.price > execution_price else None

            # Обновляем остатки
            bid.filled += executed_qty
            ask.filled += executed_qty

            if bid.filled == bid.qty:
                bid.status = StatusEnum.EXECUTED
                self.bids.pop(0)
            else:
                bid.status = StatusEnum.PARTIALLY_EXECUTED
            
            if ask.filled == ask.qty:
                ask.status = StatusEnum.EXECUTED
                self.asks.pop(0)
            else:
                ask.status = StatusEnum.PARTIALLY_EXECUTED

            trades.append(
                TradeExecution(
                    bid_order=bid,
                    ask_order=ask,
                    executed_qty=executed_qty,
                    execution_price=execution_price,
                    bid_order_change=bid_order_change
                )
            )

        return trades


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
        