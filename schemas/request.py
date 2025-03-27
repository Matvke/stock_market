import re
from pydantic import BaseModel, field_validator
from misc.enums import DirectionEnun


class NewUserRequest(BaseModel):
    name: str

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError("The name must be longer than 3 letters")
        return v
    


class OrderbookRequest(BaseModel):
    ticker: str
    direction: DirectionEnun

    @field_validator('ticker')
    def validate_ticker(cls, value):
        if not re.match(r"^[A-Z]{2,10}$", value):
            raise ValueError("Ticker validationError")
        return value