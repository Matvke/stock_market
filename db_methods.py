from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from dao.session_maker import connection
from models import User, Instrument, Balance
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO, OrderDAO
from enums import RoleEnum, DirectionEnun, StatusEnum
from uuid import uuid4
from pydantic import create_model
from schemas import Balance_Find_Pydantic, Create_Order_Pydantic, Id_Item_Pydantic, Find_Order_Pydantic, InstrumentPydantic


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
    new_user = await UserDAO.add(session=session, values=New_User_Model(name=user_data["name"], role=RoleEnum.USER, api_key=f"key-{uuid4()}"))
    return {"name": new_user.name}

# @connection(isolation_level="READ COMMITTED", commit=False) # ВЫКЛЮЧИЛ, ЧТОБЫ НЕ СОЗДАВАЛОСЬ ДВЕ СЕССИИ В МЕТОДАХ
async def get_user(user_data: dict, session: AsyncSession) -> int:
    """Ожидает на входе `user.api_key`. Возвращает `user.id` пользователя"""
    FilterModel = create_model(
        "Filter_model",
        api_key=(str, ...)
    )
    user = await UserDAO.find_one_or_none(session=session, filters=FilterModel(api_key=user_data["api_key"]))
    return user


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
    user = await get_user(user_data=user_data, session=session)
    balances = await BalanceDAO.find_all(session=session, filters=Filter_Model(user_id=user.id))
    return balances


@connection(isolation_level="SERIALIZABLE", commit=True)
async def update_balance(user_data: dict, session: AsyncSession) -> dict:
    """Запрашивает api_key, ticker, amount"""
    user = await get_user(user_data=user_data, session=session)
    if user:
        Primary_Key_Model= create_model(
            "Primary_Key_Model",
            user_id = (int, ...),
            ticker = (str, ...)
        )
        amount = int(user_data["amount"])
        return await BalanceDAO.update_balance(session=session, primary_key=Primary_Key_Model(user_id=user.id, ticker=user_data["ticker"]), amount=amount)
    else:
        return HTTPException(status_code=404)


@connection(isolation_level="READ COMMITTED", commit=False)
async def find_balance(user_data: dict, session: AsyncSession):
    return await BalanceDAO.find_one_by_primary_key(session=session, primary_key=Balance_Find_Pydantic(user_id=user_data["user_id"], ticker=user_data["ticker"]))


@connection(isolation_level="SERIALIZABLE", commit=True) # TODO рыночный ордер
async def create_order(user_data: dict, session: AsyncSession):
    try:
        user = await get_user(user_data=user_data, session=session)
        new_order = await OrderDAO.add(
            session=session, 
            values=Create_Order_Pydantic(
                user_id=user.id, 
                direction=DirectionEnun(user_data["direction"]),
                ticker=user_data["ticker"],
                qty=user_data["qty"],
                price=user_data["price"],
                status=StatusEnum.NEW,
                filled=0))
        return {"succes": True, "order_id": new_order.id}
    except Exception as e:
        raise e
    

@connection(isolation_level="READ COMMITTED", commit=False)
async def get_orderbook(user_data: dict, session: AsyncSession):
    Filter_Model = create_model(
        "Filter_Model",
        ticker=(str, ...)
    )
    limit = user_data.get("limit")
    return await OrderDAO.find_all(session=session, filters=Filter_Model(ticker=user_data["ticker"]), limit=limit)


@connection(isolation_level="READ COMMITTED", commit=False)
async def get_list_orders(user_data: dict, session: AsyncSession):
    if await get_user(user_data=user_data, session=session):
        return await OrderDAO.find_all(session=session)
    else:
        return HTTPException(status_code=404)
    

@connection(isolation_level="READ COMMITTED", commit=False)
async def get_order(user_data: dict, session: AsyncSession):
    if await get_user(user_data=user_data, session=session):
        return await OrderDAO.find_one_by_primary_key(session=session, primary_key=Id_Item_Pydantic(id=user_data["order_id"]))
    else:
        return HTTPException(status_code=404)
    

@connection(isolation_level="SERIALIZABLE", commit=True)
async def cancel_order(user_data: dict, session: AsyncSession): 
    user = await get_user(user_data=user_data, session=session)
    if user:
        await OrderDAO.delete_by_filters(session=session, primary_key=Find_Order_Pydantic(id=user_data["order_id"], user_id=user.id))
        return {"succes": True}
    else:
        return HTTPException(status_code=404)
    

@connection(isolation_level="SERIALIZABLE", commit=True)
async def add_instrument(user_data: dict, session: AsyncSession):
    user = await get_user(session=session, user_data=user_data)
    if user.role != RoleEnum.ADMIN:
        return HTTPException(status_code=403)
    else:
        await InstrumentDAO.add(session=session, values=InstrumentPydantic(ticker=user_data["ticker"], name=user_data["name"]))
        return {'succes': True}
    

@connection(isolation_level="SERIALIZABLE", commit=True)
async def delete_instrument(user_data: dict, session: AsyncSession):
    Primary_Key_Model= create_model(
    "Primary_Key_Model",
    ticker = (str, ...)
    )
    user = await get_user(session=session, user_data=user_data)
    if user.role != RoleEnum.ADMIN:
        return HTTPException(status_code=403)
    else:
        await InstrumentDAO.delete_by_filters(session=session, primary_key=Primary_Key_Model(ticker=user_data["ticker"]))
        return {'succes': True}