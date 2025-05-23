from uuid import UUID
from sqlalchemy import or_, select, update
from dao.base import BaseDAO
from misc.enums import OrderEnum, StatusEnum
from misc.db_models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession
from misc.enums import DirectionEnum
from schemas.create import BalanceCreate
from schemas.request import BalanceRequest
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError


class UserDAO(BaseDAO[User]):
    model = User


class InstrumentDAO(BaseDAO[Instrument]):
    model = Instrument
    

class BalanceDAO(BaseDAO[Balance]):
    model = Balance

    @classmethod
    async def update_balance(cls, session: AsyncSession, primary_key: BalanceRequest, amount: int) -> Balance:
        try:
            balance = await cls.find_one_by_primary_key(session=session, primary_key=primary_key)
            if balance:
                if balance.amount + amount >= 0:
                    balance.amount += amount
                else:
                    raise HTTPException(400, f"Not enough {primary_key.ticker} to withdraw")
            else:
                await cls.add(session=session, values=BalanceCreate(user_id=primary_key.user_id, ticker=primary_key.ticker, amount=amount))
            await session.flush()
            return balance
        except Exception as e:
            raise e
        

    @classmethod
    async def get_user_balances(cls, session: AsyncSession, user_id: UUID) -> dict:
        query = select(cls.model.ticker, cls.model.amount).where(cls.model.user_id == user_id)
        if hasattr(cls.model, 'visibility'):
            query = query.where(cls.model.visibility == 'ACTIVE')
        result = await session.execute(query)
        return dict(result.all())
    
    
    @classmethod
    async def transfer_assets(cls, session: AsyncSession, from_user_id: UUID, to_user_id: UUID, ticker: str, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if from_user_id == to_user_id:
            raise ValueError("Cannot transfer to self")
        # Получаем оба баланса одним запросом
        stmt = (
            select(Balance)
            .where(
                (Balance.user_id.in_([from_user_id, to_user_id]))
                & (Balance.ticker == ticker)
            )
        )
        balances = await session.execute(stmt)
        balances = {b.user_id: b for b in balances.scalars()}

        from_balance = balances.get(from_user_id)
        if not from_balance or from_balance.amount < amount:
            raise ValueError(f"User {from_user_id} do not has enough {ticker}")

        to_balance = balances.get(to_user_id)

        try:
            # Обновляем баланс отправителя
            from_balance.amount -= amount

            # Обновляем или создаем баланс получателя
            if to_balance:
                to_balance.amount += amount
            else:
                session.add(Balance(
                    user_id=to_user_id,
                    ticker=ticker,
                    amount=amount
                ))
            await session.flush()
        except SQLAlchemyError as e:
            await session.rollback()
            raise ValueError("Failed to transfer assets") from e


    @classmethod
    async def add_to_balance(cls, session: AsyncSession, user_id: UUID, ticker: str, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        balance = await cls.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=ticker))
        try:
            if balance:
                balance.amount += amount
            else:
                await cls.add(session=session, values=BalanceCreate(user_id=user_id, ticker=ticker, amount=amount))
            await session.flush()
        except SQLAlchemyError as e:
            await session.rollback()
            raise ValueError("Failed to transfer assets") from e


class OrderDAO(BaseDAO[Order]):
    model = Order

    @classmethod
    async def get_available_orders(cls, session: AsyncSession, ticker: str, except_user_id: UUID, direction: DirectionEnum) -> list[Order]:
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
            Order.price.asc() if direction == DirectionEnum.SELL else Order.price.desc(),
            Order.timestamp.asc()
        )
        .with_for_update(skip_locked=True) # Чтобы не брать ордера которые уже в процессе исполнения
        .limit(100)) 

        if hasattr(cls.model, 'visibility'):
            query = query.where(cls.model.visibility == 'ACTIVE')

        result = await session.execute(query)
        return result.scalars().all()


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
    async def update_after_trade(cls, session: AsyncSession, order_id: UUID, filled_delta: int, new_status: StatusEnum):
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(
                filled=Order.filled + filled_delta,
                status=new_status  # Это критически важно
            )
        )
        await session.flush()


class TransactionDAO(BaseDAO[Transaction]):
    model = Transaction