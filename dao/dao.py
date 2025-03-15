from sqlalchemy import Sequence, select
from dao.base import BaseDAO
from models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession


class UserDAO(BaseDAO[User]):
    model = User


class InstrumentDAO(BaseDAO[Instrument]):
    model = Instrument
    

class BalanceDAO(BaseDAO[Balance]):
    model = Balance
