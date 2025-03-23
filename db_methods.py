import uuid
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from dao.session_maker import connection
from models import User, Instrument, Balance, Transaction, Order
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO, OrderDAO, TransactionDAO
from enums import RoleEnum, DirectionEnun, StatusEnum
from uuid import uuid4
from pydantic import create_model
from schemas import *


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
async def get_user(user_data: dict, session: AsyncSession):
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
        user_id=(UUID, ...)
    )
    user = await get_user(user_data=user_data, session=session)
    balances = await BalanceDAO.find_all(session=session, filters=Filter_Model(user_id=user.id))
    return balances


@connection(isolation_level="SERIALIZABLE", commit=True)
async def update_balance(user_data: dict, session: AsyncSession):
    """Запрашивает api_key, ticker, amount"""
    user = await get_user(user_data=user_data, session=session)
    if user:
        amount = user_data["amount"]
        return await BalanceDAO.update_balance(session=session, primary_key=Balance_Find_Pydantic(user_id=user.id, ticker=user_data["ticker"]), amount=amount)
    else:
        return HTTPException(status_code=404)


@connection(isolation_level="READ COMMITTED", commit=False)
async def find_balance(user_data: dict, session: AsyncSession):
    return await BalanceDAO.find_one_by_primary_key(session=session, primary_key=Balance_Find_Pydantic(user_id=user_data["user_id"], ticker=user_data["ticker"]))


@connection(isolation_level="SERIALIZABLE", commit=True) # TODO рыночный ордер
async def create_order(user_data: dict, session: AsyncSession):
    try:
        user = await get_user(user_data=user_data, session=session)
        if not user:
            return HTTPException(status_code=404, detail="User not found")
        new_order_scheme = Create_Order_Pydantic(
            user_id=user.id,
            direction=DirectionEnun(user_data["direction"]),
            ticker=user_data["ticker"],
            qty = user_data["qty"],
            price= user_data["price"],
            status=StatusEnum.NEW,
            filled=0
        )
        user_balance = await BalanceDAO.find_one_by_primary_key(session=session, primary_key=Balance_Find_Pydantic(user_id=user.id, ticker=user_data["ticker"]))
        if not user_balance and new_order_scheme.direction == DirectionEnun.SELL:
            return HTTPException(status_code=404, detail=f"Not enough {new_order_scheme.ticker}")
        elif not user_balance:
            user_balance = await BalanceDAO.add(session=session, values=Balance_Create_Pydantic(user_id=user.id, ticker=new_order_scheme.ticker, amount=0))
        if new_order_scheme.price < 0: # Create_market_order
            print("Create_market_order")
            Filter_Model = create_model(
                "Filter_Model",
                ticker=(str, ...),
                direction=(DirectionEnun, ...),
            )
            pass 
        else: # Create_limit_order   
            if new_order_scheme.direction == DirectionEnun.SELL and user_balance.amount < new_order_scheme.qty:
                return HTTPException(405, detail=f"Not enough {new_order_scheme.ticker}")
            elif new_order_scheme.direction == DirectionEnun.SELL:
                user_balance.amount -= new_order_scheme.qty
            new_order = await OrderDAO.add(session=session, values=new_order_scheme) 
            Filter_Model = create_model(
                "Filter_Model",
                ticker=(str, ...),
                direction=(DirectionEnun, ...),
                price=(int, ...),
            )
            find_direction = DirectionEnun.SELL if new_order_scheme.direction == DirectionEnun.BUY else DirectionEnun.BUY 
            orders = await OrderDAO.find_available_orders(session=session, user_id=user.id, filters=Filter_Model(ticker=new_order_scheme.ticker, direction=find_direction, price=new_order.price))
            for existed_order in orders:
                if new_order.price == existed_order.price and new_order.direction == DirectionEnun.BUY: # Покупает
                    new_order_free_units = new_order.qty - new_order.filled # Сколько еще может купить
                    existed_order_free_units = existed_order.qty - existed_order.filled # Сколько еще может продать
                    if new_order_free_units > existed_order_free_units:
                        new_order.filled += existed_order_free_units
                        existed_order.filled += existed_order_free_units
                        await TransactionDAO.add(session=session, values=
                                                Create_Transaction_Pydantic(
                                                    buyer_id=new_order.user_id,
                                                    seller_id=existed_order.user_id,
                                                    ticker=new_order.ticker,
                                                    amount=existed_order_free_units,
                                                    price=new_order.price))
                    else:
                        transaction_amount = existed_order_free_units - (existed_order_free_units - new_order_free_units)
                        new_order.filled += transaction_amount
                        existed_order.filled += transaction_amount
                        await TransactionDAO.add(session=session, values=
                                                Create_Transaction_Pydantic(
                                                    buyer_id=new_order.user_id,
                                                    seller_id=existed_order.user_id,
                                                    ticker=new_order.ticker,
                                                    amount=transaction_amount,
                                                    price=new_order.price))
                    if new_order.filled == new_order.qty:
                        new_order.status = StatusEnum.EXECUTED
                        user_balance.amount += new_order.qty
                    else:
                        new_order.status = StatusEnum.PARTIALLY_EXECUTED
                    if existed_order.filled == existed_order.qty:
                        existed_order.status = StatusEnum.EXECUTED
                    else:
                        existed_order.status = StatusEnum.PARTIALLY_EXECUTED
                    
                elif new_order.price == existed_order.price and new_order.direction == DirectionEnun.SELL: # Продает
                    new_order_free_units = new_order.qty - new_order.filled # Сколько еще может продать
                    existed_order_free_units = existed_order.qty - existed_order.filled # Сколько еще может купить
                    if new_order_free_units > existed_order_free_units: # Может купить больше чем есть
                        new_order.filled += existed_order_free_units
                        existed_order.filled += existed_order_free_units
                        await TransactionDAO.add(session=session, values=
                                                Create_Transaction_Pydantic(
                                                    buyer_id=existed_order.user_id,
                                                    seller_id=new_order.user_id,
                                                    ticker=new_order.ticker,
                                                    amount=existed_order_free_units,
                                                    price=new_order.price))
                    else: # Не может купить столько, сколько есть
                        transaction_amount = existed_order_free_units - (existed_order_free_units - new_order_free_units)
                        new_order.filled += transaction_amount
                        existed_order.filled += transaction_amount
                        await TransactionDAO.add(session=session, values=
                                                Create_Transaction_Pydantic(
                                                    buyer_id=existed_order.user_id,
                                                    seller_id=new_order.user_id,
                                                    ticker=new_order.ticker,
                                                    amount=transaction_amount,
                                                    price=new_order.price))
                    if new_order.filled == new_order.qty:
                        new_order.status = StatusEnum.EXECUTED
                        user_balance.amount += new_order.qty
                    else:
                        new_order.status = StatusEnum.PARTIALLY_EXECUTED
                    if existed_order.filled == existed_order.qty:
                        existed_order.status = StatusEnum.EXECUTED
                    else:
                        existed_order.status = StatusEnum.PARTIALLY_EXECUTED
        await session.flush()
        return {"succes": True, "order_id": new_order.id}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error {e}")


@connection(isolation_level="READ COMMITTED", commit=False)
async def get_orderbook(user_data: dict, session: AsyncSession):
    limit = user_data.get("limit")
    return await OrderDAO.find_all(session=session, filters=Find_Order_By_Ticker_Pydantic(ticker=user_data["ticker"]), limit=limit)


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