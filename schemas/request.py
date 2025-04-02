import re
from pydantic import BaseModel, field_validator
from misc.enums import DirectionEnun
from uuid import UUID


class NewUserRequest(BaseModel):
    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError("The name must be longer than 3 letters")
        return v
    

class UserAPIRequest(BaseModel):
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
    


class OrderbookRequest(BaseModel):
    ticker: str
    direction: DirectionEnun

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
    
