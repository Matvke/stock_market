from urllib.error import HTTPError
from sqlalchemy import Sequence, select, update
from dao.base import BaseDAO
from models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, create_model
from schemas import Balance_Find_Pydantic


class UserDAO(BaseDAO[User]):
    model = User


class InstrumentDAO(BaseDAO[Instrument]):
    model = Instrument
    

class BalanceDAO(BaseDAO[Balance]):
    model = Balance

    @classmethod
    async def update_balance(cls, session: AsyncSession, primary_key: BaseModel, amount: int):
        try:
            balance = await cls.find_one_by_primary_key(session=session, primary_key=primary_key)
            if balance:
                balance.amount += amount
            else:
                Add_Model = create_model(
                    "Add_Model",
                    user_id=(int, ...),
                    ticker=(str, ...),
                    amount=(int, ...)
                )
                await cls.add(session=session, values=Add_Model(user_id=primary_key.user_id, ticker=primary_key.ticker, amount=amount))
                await session.flush()
            return {"success": True}
        except Exception as e:
            raise e


class OrderDAO(BaseDAO[Order]):
    model = Order


class TransactionDAO(BaseDAO[Transaction]):
    model = Transaction