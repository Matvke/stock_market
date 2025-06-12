from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from dao.base import BaseDAO
from misc.enums import OrderEnum, StatusEnum
from misc.db_models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession


class UserDAO(BaseDAO[User]):
    model = User


class InstrumentDAO(BaseDAO[Instrument]):
    model = Instrument
    

class BalanceDAO(BaseDAO[Balance]):
    model = Balance

        
    @classmethod
    async def upsert_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int):
        stmt = insert(cls.model).values(user_id=user_id, ticker=ticker, amount=amount)
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "ticker"],
            set_={"amount": cls.model.amount + amount}
        ) 
        await session.execute(stmt)
        await session.flush()


    @classmethod
    async def get_user_balances(cls, session: AsyncSession, user_id: UUID) -> dict:
        balances = (await session.execute(
            select(cls.model.ticker, cls.model.amount, cls.model.blocked_amount)
            .where(cls.model.user_id == user_id))).all()
        return {
            balance.ticker: balance.amount + balance.blocked_amount
            for balance in balances
        }
    
    @classmethod
    async def get_balance_with_lock(cls, session: AsyncSession, user_id: UUID, ticker: str) -> Balance:
        balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == user_id,
                   Balance.ticker == ticker)
            .with_for_update(of=[Balance.amount])
        )).scalar_one_or_none()
        return balance
    

    @classmethod
    async def block_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
            return False
        
        balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == user_id, Balance.ticker == ticker)
            .with_for_update()
        )).scalar_one_or_none()

        if not balance or balance.amount < amount:
            return False
        
        balance.amount -= amount
        balance.blocked_amount += amount
        return True
    

    @classmethod
    async def unblock_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
           return False

        balance = (await session.execute(
            select(Balance)
            .where(Balance.user_id == user_id, Balance.ticker == ticker)
            .with_for_update()
        )).scalar_one_or_none()

        if not balance or balance.blocked_amount < amount:
            return False 

        balance.blocked_amount -= amount
        balance.amount += amount
        return True
    

    @classmethod
    async def transfer_balance(cls, session: AsyncSession, from_user_id: UUID, to_user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
           return False
        
        # 1. Лочим отправителя
        from_balance = (await session.execute(
            select(Balance)
            .where(
                Balance.user_id == from_user_id, 
                Balance.ticker == ticker)
            .with_for_update()
        )).scalar_one_or_none()

        if not from_balance or from_balance.blocked_amount < amount:
            return False
        
        from_balance.blocked_amount -= amount

        # 2. Лочим получателя
        to_balance = (await session.execute(
            select(Balance)
            .where(
                Balance.user_id == to_user_id,
                Balance.ticker == ticker
            )
            .with_for_update()
        )).scalar_one_or_none()

        if to_balance:
            to_balance.amount += amount
        else:
            session.add(Balance(user_id=to_user_id, ticker=ticker, amount=amount, blocked_amount=0))


class OrderDAO(BaseDAO[Order]):
    model = Order

    @classmethod
    async def get_open_orders(cls, session: AsyncSession, ticker: str) -> list[Order]:
        query = (select(cls.model).where(
            cls.model.ticker == ticker,
            cls.model.order_type == OrderEnum.LIMIT,
            cls.model.status.in_([StatusEnum.NEW, StatusEnum.PARTIALLY_EXECUTED])
        ))    
        result = await session.execute(query)
        return result.scalars().all()
    

    @classmethod
    async def update_after_trade(cls, session: AsyncSession, order_id: UUID, new_filled: int, new_status: StatusEnum):
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                filled=new_filled,
                status=new_status 
            )
        )
        await session.flush()



    @classmethod
    async def get_order_by_id_with_for_update(cls, session: AsyncSession, order_id: UUID, user_id: UUID):
        order = await session.execute(
            select(Order)
            .where(Order.id == order_id, Order.user_id == user_id)
            .with_for_update() #Уменьшает количество рассинхронов, но пиздец как бьет по скорости.
        )
        order = order.scalar_one_or_none()
        return order


class TransactionDAO(BaseDAO[Transaction]):
    model = Transaction