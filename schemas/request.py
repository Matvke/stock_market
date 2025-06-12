import re
from pydantic import BaseModel, ConfigDict, field_validator, UUID4, Field
from misc.enums import DirectionEnum, RoleEnum, StatusEnum
from uuid import UUID


class IdRequest(BaseModel):
    id: UUID4


class NewUserRequest(BaseModel):
    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError("The name must be longer than 3 letters")
        return v
    

class UserAPIRequest(BaseModel):
    api_key: str
    role: RoleEnum | None = RoleEnum.USER

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
    

class OrderbookRequest(BaseModel):
    ticker: str
    direction: DirectionEnum

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value
    

class TransactionRequest(BaseModel):
    ticker: str

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value
    

class OrderRequest(BaseModel):
    user_id: UUID4 
    id: UUID4 | None = None
    status: StatusEnum | None = None
    direction: DirectionEnum | None = None
    ticker: str | None = None

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value


class LimitOrderRequest(BaseModel):
    direction: DirectionEnum
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")
    qty: int = Field(..., gt=0)
    price: int = Field(..., gt=0)


class MarketOrderRequest(BaseModel):
    direction: DirectionEnum
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")
    qty: int = Field(..., gt=0)

    model_config = ConfigDict(extra="forbid")


class BalanceRequest(BaseModel):
    user_id: UUID4
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")


class InstrumentRequest(BaseModel):
    name: str
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")


class DepositRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)


class WithdrawRequest(BaseModel):
    user_id: UUID4
    ticker: str
    amount: int = Field(..., gt=0)


class TickerRequest(BaseModel):
    ticker: str = Field(..., min_length=2, max_length=10, pattern="^[A-Z]+$")