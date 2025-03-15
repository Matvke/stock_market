from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Generic, TypeVar, List
from dao.database import Base

# Типовой параметр T наследники Base
T = TypeVar("T", bound=Base)

class BaseDAO(Generic[T]):
    """Базовый класс для работы с базой данных, который предоставляет универсальные методы для добавления данных в таблицы.
    \n```model = type[T]

    @classmethod
    async def add(cls, session: AsyncSession, **values):"""
    model: type[T]

    @classmethod
    async def add(cls, session: AsyncSession, values: BaseModel):
        """Добавляет одну запись в таблицу"""
        values_dict = values.model_dump(exclude_unset=True)
        new_instance = cls.model(**values_dict)
        session.add(new_instance)
        try:
            await session.flush()
        except SQLAlchemyError as e:
            await session.rollback()
            raise e
        return new_instance
    

    @classmethod 
    async def find_all(cls, session: AsyncSession, filters: BaseModel | None):
        """Поиск всех записей удовлетворяющих условию"""
        if filters:
            filter_dict = filters.model_dump(exclude_unset=True)
        else:
            filter_dict = {}
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query)
            return result.scalars().all()
        except SQLAlchemyError as e:
            raise e
    

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, filters: BaseModel):
        """Поиск одного или нулл по условию"""
        filter_dict = filters.model_dump(exclude_unset=True)
        try:
            query = select(cls.model).filter_by(**filter_dict)
            result = await session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
