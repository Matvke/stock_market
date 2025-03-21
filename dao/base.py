from dataclasses import field
from tkinter import NO
from urllib.error import HTTPError
from sqlalchemy import select, update
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
    async def find_all(cls, session: AsyncSession, filters: BaseModel | None = None, limit: int | None = None):
        """Поиск всех записей удовлетворяющих условию"""
        if filters:
            filter_dict = filters.model_dump(exclude_unset=True)
        else:
            filter_dict = {}
        try:
            query = select(cls.model).filter_by(**filter_dict).limit(limit)
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


    @classmethod
    async def update_one_by_primary_key(cls, session: AsyncSession, primary_key: BaseModel, updated_values: BaseModel | None = None, incremented_values: BaseModel | None = None):
        """Обновление значений на новое или прибавление к значению"""
        values_dict = updated_values.model_dump(exclude_unset=True) if updated_values else None
        increments_dict = incremented_values.model_dump(exclude_unset=True) if incremented_values else None
        try: 
            record = await cls.find_one_by_primary_key(session=session, primary_key=primary_key)
            if values_dict:
                for key, value in values_dict.items():
                    setattr(record, key, value)

            if increments_dict:
                for key, value in increments_dict.items():
                    setattr(record, key, getattr(record, key) + value)

            await session.flush()
            return {"succes": True}
        except Exception as e:
            raise e


    @classmethod
    async def find_one_by_primary_key(cls, session: AsyncSession, primary_key: BaseModel):
        """Поиск по составному или обычному ключу"""
        keys_dict = primary_key.model_dump(exclude_unset=True)
        return await session.get(cls.model, keys_dict)


    @classmethod
    async def delete_one_by_primary_key(cls, session: AsyncSession, primary_key: BaseModel):
        keys_dict = primary_key.model_dump(exclude_unset=True)
        record = await session.get(cls.model, keys_dict)
        return await session.delete(record)
    

    @classmethod
    async def delete_by_filters(cls, session: AsyncSession, primary_key: BaseModel):
        record = await cls.find_one_or_none(session=session, filters=primary_key)
        if record:
            await session.delete(record)
            return {"secces": True}
        else:
            return HTTPError(code=404)