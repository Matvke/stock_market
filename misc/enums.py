import enum


class RoleEnum(str, enum.Enum): 
    USER = 'USER'
    ADMIN = 'ADMIN'


class DirectionEnun(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class StatusEnum(str, enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class OrderEnum(str, enum.Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"