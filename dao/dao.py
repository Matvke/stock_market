from urllib.error import HTTPError
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy import Sequence, or_, select, update
from dao.base import BaseDAO
from enums import StatusEnum
from models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, create_model
from schemas import Balance_Create_Pydantic, Create_Order_Pydantic


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
                await cls.add(session=session, values=Balance_Create_Pydantic(user_id=primary_key.user_id, ticker=primary_key.ticker, amount=amount))
                await session.flush()
            return {"success": True}
        except Exception as e:
            raise e


class OrderDAO(BaseDAO[Order]):
    model = Order

    @classmethod
    async def find_available_orders(cls, session: AsyncSession, filters: BaseModel, user_id: UUID):
        query = select(cls.model).where(
            cls.model.user_id != user_id,
            or_(
                cls.model.status == StatusEnum.NEW,
                cls.model.status == StatusEnum.PARTIALLY_EXECUTED
            )
        )

        if filters:
            filter_dict = filters.model_dump(exclude_unset=True)
            query = query.filter_by(**filter_dict)

        result = await session.execute(query)
        orders = result.scalars().all()

        if not orders:
            raise HTTPException(status_code=404, detail="Orders not found")
        
        return orders


class TransactionDAO(BaseDAO[Transaction]):
    model = Transaction