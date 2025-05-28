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
    async def block_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
            return False
        
        result = await session.execute(
            update(Balance)
            .where(Balance.user_id == user_id, 
                   Balance.ticker == ticker,
                   Balance.amount >= amount)
            .values(
                amount = Balance.amount - amount,
                blocked_amount = Balance.blocked_amount + amount)
            .returning(Balance.user_id))
        await session.flush()

        return len(result.scalars().all()) > 0
    
    @classmethod
    async def unblock_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
           return False

        result = await session.execute(
            update(Balance)
            .where(
                Balance.user_id == user_id,
                Balance.ticker == ticker,
                Balance.blocked_amount >= amount   
            )
            .values(
                amount=Balance.amount + amount,
                blocked_amount=Balance.blocked_amount - amount
            )
            .returning(Balance.user_id)
        )
        
        await session.flush()
        return len(result.scalars().all()) > 0
    

    @classmethod
    async def transfer_balance(cls, session: AsyncSession, from_user_id: UUID, to_user_id: UUID, ticker: str, amount: int) -> bool:
        if amount <= 0:
           return False
        # 1. Атомарно списываем с отправителя (только если blocked_amount >= amount)
        debit_success = await session.execute(
            update(Balance)
            .where(
                Balance.user_id == from_user_id,
                Balance.ticker == ticker,
                Balance.blocked_amount >= amount  # Проверка достаточности средств
            )
            .values(blocked_amount=Balance.blocked_amount - amount)
            .returning(Balance.user_id)
        )
        
        if not debit_success.scalar():
            return False  # Не хватило средств или нет баланса

        # 2. UPSERT для получателя (создаем баланс если не существует)
        await session.execute(
            insert(Balance)
            .values(
                user_id=to_user_id,
                ticker=ticker,
                amount=amount,
                blocked_amount=0
            )
            .on_conflict_do_update(
                index_elements=["user_id", "ticker"],  # Условие конфликта (primary key)
                set_={
                    "amount": Balance.amount + amount  # Если запись есть - увеличиваем amount
                }
            )
        )
        
        await session.flush()
        return True

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