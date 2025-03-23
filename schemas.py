from typing import List
from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
from dao.database import Base
from enums import DirectionEnun, RoleEnum, StatusEnum
import re


class UserPydantic(BaseModel):
    id: UUID
    name: str
    role: RoleEnum
    api_key: str

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class InstrumentPydantic(BaseModel):
    name: str
    ticker: str

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value
    
    model_config = ConfigDict(from_attributes=True)


class Balance_Create_Pydantic(BaseModel):
    user_id: UUID
    ticker: str
    amount: int

    model_config = ConfigDict(from_attributes=True)


class Balance_Output_Pydantic(BaseModel):
    ticker: str
    amount: int

    model_config = ConfigDict(from_attributes=True)


class Balance_Find_Pydantic(BaseModel):
    user_id: UUID
    ticker: str

    model_config = ConfigDict(from_attributes=True)


class Create_Order_Pydantic(BaseModel):
    user_id: UUID
    direction: DirectionEnun
    ticker: str
    qty: int
    price: int
    status: StatusEnum
    filled: int

    @field_validator("qty")
    def check_qty(cls, value):
        if value < 1:
            raise ValueError('Меньше 1')
        return value
    
    @field_validator("price")
    def check_price(cls, value):
        if value < 0:
            raise ValueError('Меньше или равно 0')
        return value


    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class Show_Order_Pydantic(BaseModel):
    id: UUID
    user_id: UUID
    ticker: str
    direction: DirectionEnun
    qty: int
    price: int
    status: StatusEnum
    filled: int

    model_config = ConfigDict(from_attributes=True)


class Id_Item_Pydantic(BaseModel):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class Find_Order_Pydantic(BaseModel):
    id: UUID
    user_id: UUID

    model_config = ConfigDict(from_attributes=True)


class Find_Order_By_Ticker_Pydantic(BaseModel):
    ticker: str

    model_config = ConfigDict(from_attributes=True)


class Create_Transaction_Pydantic(BaseModel):
    buyer_id: UUID
    seller_id: UUID
    ticker: str
    amount: int
    price: int