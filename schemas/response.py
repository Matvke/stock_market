from pydantic import BaseModel, ConfigDict, field_validator
from misc.enums import *
from uuid import UUID
import re
from typing import List


class UserResponse(BaseModel):
    id: UUID
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

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value

    model_config = ConfigDict(from_attributes=True)


class Level(BaseModel):
    price: int
    qty: int

    model_config = ConfigDict(from_attributes=True)


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]



