from pydantic import BaseModel, Field, field_validator, ConfigDict, UUID4
from misc.enums import DirectionEnum, RoleEnum, OrderEnum
from uuid import UUID


class UserCreate(BaseModel):
    name: str
    role: RoleEnum
    api_key: str  # Формат "key-<UUID>"

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError("The name must be longer than 3 letters")
        return v
    

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


class LimitOrderCreate(BaseModel):
    user_id: UUID4
    direction: DirectionEnum
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")
    qty: int = Field(..., gt=0)
    price: int = Field(..., gt=0)
    order_type: OrderEnum = OrderEnum.LIMIT


class MarketOrderCreate(BaseModel):
    user_id: UUID4
    direction: DirectionEnum
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")
    qty: int = Field(..., gt=0)
    order_type: OrderEnum = OrderEnum.MARKET
    

class CancelOrderCreate(BaseModel):
    id: UUID4
    

class BalanceCreate(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = 0
    blocked_amount: int = 0


class TransactionCreate(BaseModel):
    buyer_id: UUID4
    seller_id: UUID4
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")
    amount: int = Field(..., gt=0)
    price: int = Field(..., gt=0)
