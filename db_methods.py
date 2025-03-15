from sqlalchemy.ext.asyncio import AsyncSession
from dao.session_maker import connection
from models import User, Instrument, Balance
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO
from enums import RoleEnum
from uuid import uuid4
from pydantic import create_model
# from dao.database import connection


@connection(isolation_level="SERIALIZABLE")
async def register(user_data: dict, session: AsyncSession) -> User:
    """Ожидает на входе имя пользователя\n
    Добавляет пользователя и дает ему API ключ.""" 
    New_User_Model = create_model(
        "New_User",
        name=(str, ...),
        role=(RoleEnum, ...),
        api_key=(str, ...)
    )

    return await UserDAO.add(session=session, values=New_User_Model(name=user_data["name"], role=RoleEnum.USER, api_key=f"key-{uuid4()}"))


# @connection(isolation_level="READ COMMITTED", commit=False) # ВЫКЛЮЧИЛ, ЧТОБЫ НЕ СОЗДАВАЛОСЬ ДВЕ СЕССИИ В МЕТОДЕ GET_BALANCES
async def get_user_id(user_data: dict, session: AsyncSession) -> int:
    """Ожидает на входе `user.api_key`. Возвращает `user.id` пользователя"""
    FilterModel = create_model(
        "Filter_model",
        api_key=(str, ...)
    )
    user = await UserDAO.find_one_or_none(session=session, filters=FilterModel(api_key=user_data["api_key"]))
    return user.id


@connection(isolation_level="READ COMMITTED", commit=False)
async def get_instruments_list(session: AsyncSession) -> list[Instrument]:
    """Возвращает весь список инструментов"""
    return await InstrumentDAO.find_all(session=session, filters=None)


@connection(isolation_level="READ COMMITTED", commit=False)
async def get_balances(user_data: dict, session: AsyncSession) -> list[Balance]:
    """Запрашивает `{"api_key": "example"}` пользователя. Возвращает баланс пользователя"""
    Filter_Model = create_model(
        "Filter_Model",
        user_id=(int, ...)
    )
    user_id = await get_user_id(user_data=user_data, session=session) 
    balances = await BalanceDAO.find_all(session=session, filters=Filter_Model(user_id=user_id))
    return balances