from typing import List
from pydantic import BaseModel, ConfigDict, field_validator
from dao.database import Base
from enums import DirectionEnun, RoleEnum, StatusEnum


class UserPydantic(BaseModel):
    id: int # TODO str
    name: str
    role: RoleEnum
    api_key: str

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class InstrumentPydantic(BaseModel):
    name: str
    ticker: str

    model_config = ConfigDict(from_attributes=True)


class Balance_Output_Pydantic(BaseModel):
    ticker: str
    amount: int

    model_config = ConfigDict(from_attributes=True)


class Balance_Find_Pydantic(BaseModel):
    user_id: int
    ticker: str

    model_config = ConfigDict(from_attributes=True)


class Create_Order_Pydantic(BaseModel):
    user_id: int
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
        if value <= 0:
            raise ValueError('Меньше или равно 0')
        return value


    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class Show_Order_Pydantic(BaseModel):
    id: int
    status: StatusEnum
    user_id: int
    direction: DirectionEnun
    ticker: str
    qty: int
    price: int
    filled: int

    model_config = ConfigDict(from_attributes=True)


class Id_Item_Pydantic(BaseModel):
    id: int

    model_config = ConfigDict(from_attributes=True)



class Find_Order_Pydantic(BaseModel):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)