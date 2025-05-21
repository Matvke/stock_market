from dataclasses import dataclass
from uuid import UUID, uuid4
from misc.enums import DirectionEnum, OrderEnum, StatusEnum
from misc.db_models import Order
from datetime import datetime, timezone


@dataclass
class InternalOrder:
    user_id: UUID
    direction: DirectionEnum
    ticker: str
    qty: int
    order_type: OrderEnum
    price: int | None
    id: UUID = uuid4
    timestamp: datetime = datetime.now(timezone.utc)
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
            timestamp=order.timestamp if order.timestamp.tzinfo else order.timestamp.replace(tzinfo=timezone.utc),
        )


@dataclass
class TradeExecution:
    bid_order: InternalOrder  # Ордер на покупку
    ask_order: InternalOrder  # Ордер на продажу
    executed_qty: int         # Количество исполненных активов
    execution_price: int      # Цена исполнения (берется от ask ордера)
    bid_order_change: int | None = None  # Сдача для bid ордера (если есть)