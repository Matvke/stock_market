from sqlalchemy.orm import DeclarativeBase, class_mapper
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from config import settings


DATABASE_URL = settings.get_db_url()

# Асинхронный движок БД
engine = create_async_engine(
    DATABASE_URL,
    pool_size=30,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
)

# Фабрика сессий
async_session_maker = async_sessionmaker(engine, expire_on_commit=True)


class Base(AsyncAttrs, DeclarativeBase):
    """Базовый класс для всех моделей"""
    __abstract__ = True


    def to_dict(self) -> dict:
        """Возвращает словарь всех полей модели"""
        columns = class_mapper(self.__class__).columns
        return {column.key: getattr(self, column.key) for column in columns}
