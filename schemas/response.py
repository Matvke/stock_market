from pydantic import BaseModel, ConfigDict, field_validator, RootModel, UUID4
from misc.db_models import Order
from misc.enums import *
from uuid import UUID
import re
from typing import List, Dict
from datetime import datetime


class UserResponse(BaseModel):
    id: UUID4
    name: str
    role: RoleEnum
    api_key: str 

    @field_validator('api_key')
    def validate_api_key(cls, v):
        if not v.startswith('key-'):
            raise ValueError("API key must start with 'key-'")
        
        uuid_part = v[4:]  # Отрезаем 'key-'
        try:
            UUID(uuid_part)  # Проверяем, что это валидный UUID
        except ValueError:
            raise ValueError("Invalid UUID part in API key")
        
        return v

    model_config = ConfigDict(from_attributes=True)



class InstrumentResponse(BaseModel):
    name: str
    ticker: str

    model_config = ConfigDict(from_attributes=True)


class Level(BaseModel):
    price: int
    qty: int

    model_config = ConfigDict(from_attributes=True)


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]


class TransactionResponse(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class BalanceResponse(RootModel):
    root: Dict[str, int]

    model_config = ConfigDict(from_attributes=True)


class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: UUID4

    model_config = ConfigDict(json_encoders={UUID4: str})


class LimitOrderBody(BaseModel):
    direction: DirectionEnun
    ticker: str
    qty: int
    price: int


class LimitOrderResponse(BaseModel):
    id: UUID4
    status: StatusEnum
    user_id: UUID4
    timestamp: datetime
    body: LimitOrderBody
    filled: int

    model_config = ConfigDict(json_encoders={UUID4: str})


class MarketOrderBody(BaseModel):
    direction: DirectionEnun
    ticker: str
    qty: int


class MarketOrderResponse(BaseModel):
    id: UUID4
    status: StatusEnum
    user_id: UUID4
    timestamp: datetime
    body: MarketOrderBody

    model_config = ConfigDict(json_encoders={UUID4: str})


def convert_order(order: Order) -> MarketOrderResponse | LimitOrderResponse:
    if order.price:
        body = LimitOrderBody(
            direction=order.direction,
            ticker=order.ticker,
            qty=order.qty,
            price=order.price
        )

        return LimitOrderResponse(
            id=order.id,
            status=order.status,
            user_id=order.user_id,
            timestamp=order.timestamp,
            body=body,
            filled=order.filled
        )
    else:
        body = MarketOrderBody(
            direction=order.direction,
            ticker=order.ticker,
            qty=order.ticker
        )

        return MarketOrderResponse(
            id=order.id,
            status=order.status,
            user_id=order.user_id,
            timestamp=order.timestamp,
            body=body
        )
    

class OkResponse(BaseModel):
    success: bool = True
