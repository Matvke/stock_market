from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    """Базовый класс для работы с базой данных, который предоставляет универсальные методы для добавления данных в таблицы.
    \n```model = None

    @classmethod
    async def add(cls, session: AsyncSession, **values):"""
    model = None

    @classmethod
    async def add(cls, session: AsyncSession, **values):
        """Добавляет одну запись в таблицу"""
        new_instance = cls.model(**values)
        session.add(new_instance)
        try:
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise e
        return new_instance