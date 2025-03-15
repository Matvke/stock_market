from sqlalchemy import Integer, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, class_mapper
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from config import settings


DATABASE_URL = settings.get_db_url()

# Асинхронный движок БД
engine = create_async_engine(url=DATABASE_URL)

# Фабрика сессий
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей"""
    __abstract__ = True


    def to_dict(self) -> dict:
        """Возвращает словарь всех полей модели"""
        columns = class_mapper(self.__class__).columns
        return {column.key: getattr(self, column.key) for column in columns}


def connection(method):
    """`depreceted`
    Асинхронная фабрика сессий.\n
    Автоматизирует открытие и закрытие сессий для работы с БД.\n
    Пример использования:\n
    ```@connection
    async def get_users(session):
        return await session.execute(select(User))"""
    async def wrapper(*args, **kwargs):
        async with async_session_maker() as session: 
            try:
                return await method(*args, session=session, **kwargs)
            except Exception as e:
                await session.rollback()
                raise e
            finally:
                await session.close()
    return wrapper