from typing import List
from pydantic import BaseModel, ConfigDict
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


class BalancePydantic(BaseModel):
    ticker: str
    amount: int

    model_config = ConfigDict(from_attributes=True)