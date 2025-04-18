from dataclasses import dataclass
from uuid import UUID
from schemas.create import TransactionCreate
from misc.enums import DirectionEnum, OrderEnum, StatusEnum
from misc.db_models import Order
from copy import deepcopy


@dataclass
class InternalOrder:
    id: UUID
    user_id: UUID
    direction: DirectionEnum
    ticker: str
    qty: int
    order_type: OrderEnum
    price: int | None
    filled: int = 0
    status: StatusEnum = StatusEnum.NEW

    @property
    def remaining(self) -> int:
        return self.qty - self.filled
    
    @staticmethod
    def from_db(order: Order) -> "InternalOrder":
        return InternalOrder(
            id=order.id,
            user_id=order.user_id,
            direction=order.direction,
            ticker=order.ticker,
            qty=order.qty,
            price=order.price,
            filled=order.filled,
            order_type=order.order_type,
            status=order.status,
        )


@dataclass
class TradeExecution:
    bid_order: InternalOrder  # Ордер на покупку
    ask_order: InternalOrder  # Ордер на продажу
    executed_qty: int         # Количество исполненных активов
    execution_price: int      # Цена исполнения (берется от ask ордера)
    bid_order_change: int | None = None  # Сдача для bid ордера (если есть)

    def __post_init__(self):
        self.bid_order = deepcopy(self.bid_order)
        self.ask_order = deepcopy(self.ask_order)