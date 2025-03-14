from sqlalchemy.ext.asyncio import AsyncSession
from database import connection
from models import User, Instrument, Balance
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO


@connection
async def register(user_data: dict, session: AsyncSession) -> User:
    """Ожидает на входе имя пользователя\n
    Добавляет пользователя и дает ему API ключ.""" 
    return await UserDAO.register(session=session, user_data=user_data)


@connection
async def get_user_key(user_data: dict, session: AsyncSession) -> int:
    """Ожидает на входе `user.api_key`. Возвращает `user.id` пользователя"""
    return await UserDAO.get_user_id(session=session, user_data=user_data)


@connection
async def get_instruments_list(session: AsyncSession) -> list[Instrument]:
    """Возвращает весь список инструментов"""
    return await InstrumentDAO.get_instruments_list(session=session)


@connection
async def get_balances(user_data: dict, session: AsyncSession) -> list[Balance]:
    """Запрашивает `{"api_key": "example"}` пользователя. Возвращает баланс пользователя"""
    user_id = await get_user_key(user_data=user_data)
    balances = await BalanceDAO.get_balances(session=session, user_data=user_id)
    return balances