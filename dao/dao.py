from sqlalchemy import Sequence, select
from dao.base import BaseDAO
from models import User, Transaction, Balance, Instrument, Order
from sqlalchemy.ext.asyncio import AsyncSession
from enums import RoleEnum
import uuid


class UserDAO(BaseDAO):
    model = User

    @classmethod
    async def register(cls, session: AsyncSession, user_data: dict) -> User:
        """Ожидает на входе имя пользователя\n
        Добавляет пользователя и дает ему API ключ."""
        def __generate_api(length=10):
            return f"key-{uuid.uuid4()}"
    
        user = cls.model(
            name=user_data['name'],
            role=RoleEnum.USER,
            api_key=__generate_api() 
        )
        session.add(user)
        await session.commit()
        return user
    

    @classmethod
    async def get_user_id(cls, session: AsyncSession, user_data: dict) -> int:
        """Ожидает на входе `user.api_key`. Возвращает `{"id": "user.id"}`"""
        query = select(cls.model).where(cls.model.api_key == user_data["api_key"])
        result = await session.execute(query)
        records = result.scalar()
        return {"id": records.id}


class InstrumentDAO(BaseDAO):
    model = Instrument

    @classmethod
    async def get_instruments_list(cls, session: AsyncSession) -> list[Instrument]:
        query = select(cls.model)
        result = await session.execute(query)
        records = result.scalars().all() # Запрашиваем всю модель scalars() и всек записи all()
        return records
    

class BalanceDAO(BaseDAO):
    model = Balance

    @classmethod
    async def get_balances(cls, session: AsyncSession, user_data: dict) -> list[Balance]:
        """Запрашивает `user.id` чтобы вернуть список всех балансов пользователя"""
        query = select(cls.model).where(cls.model.user_id == user_data['id'])
        result = await session.execute(query)
        records = result.scalars().all()
        return records