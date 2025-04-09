from uuid import UUID
from sqlalchemy import or_, select
from dao.base import BaseDAO
from misc.enums import OrderEnum, StatusEnum
from misc.db_models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from misc.enums import DirectionEnun
from schemas.create import BalanceCreate


class UserDAO(BaseDAO[User]):
    model = User


class InstrumentDAO(BaseDAO[Instrument]):
    model = Instrument
    

class BalanceDAO(BaseDAO[Balance]):
    model = Balance

    @classmethod
    async def update_balance(cls, session: AsyncSession, primary_key: BaseModel, amount: int) -> Balance:
        try:
            balance = await cls.find_one_by_primary_key(session=session, primary_key=primary_key)
            if balance:
                balance.amount += amount
            else:
                await cls.add(session=session, values=BalanceCreate(user_id=primary_key.user_id, ticker=primary_key.ticker, amount=amount))
                await session.flush()
            return balance
        except Exception as e:
            raise e
        

    @classmethod
    async def get_user_balances(cls, session: AsyncSession, user_id: UUID) -> dict:
        result = await session.execute(
            select(cls.model.ticker, cls.model.amount)
            .where(cls.model.user_id == user_id)
        )
        return dict(result.all())


class OrderDAO(BaseDAO[Order]):
    model = Order

    @classmethod
    async def find_available_orders(cls, session: AsyncSession, filters: BaseModel, user_id: UUID) -> list[Order]:
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

        # if not orders:
        #     raise HTTPException(status_code=404, detail="Orders not found")
        
        return orders
    

    @classmethod
    async def get_available_orders(cls, session: AsyncSession, ticker: str, except_user_id: UUID, direction: DirectionEnun) -> list[Order]:
        query = (select(cls.model).where(
            cls.model.user_id != except_user_id,
            cls.model.ticker == ticker,
            cls.model.direction != direction,
            cls.model.order_type != OrderEnum.MARKET,
            or_(
                cls.model.status == StatusEnum.NEW,
                cls.model.status == StatusEnum.PARTIALLY_EXECUTED
            )
        )
        .order_by(
            Order.price.asc() if direction == DirectionEnun.SELL else Order.price.desc(),
            Order.timestamp.asc()
        )
        .with_for_update(skip_locked=True) # Чтобы не брать ордера которые уже в процессе исполнения
        .limit(100)) 
        result = await session.execute(query)
        return result.scalars().all()


class TransactionDAO(BaseDAO[Transaction]):
    model = Transaction