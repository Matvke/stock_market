from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from dao.session_maker import connection
from misc.db_models import User, Instrument, Balance
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO, OrderDAO, TransactionDAO
from misc.enums import RoleEnum, DirectionEnun, StatusEnum
from uuid import uuid4
from pydantic import create_model
from old_schemas import *


@connection(isolation_level="SERIALIZABLE", commit=True)
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
        raise HTTPException(status_code=404)


@connection(isolation_level="READ COMMITTED", commit=False)
async def find_balance(user_data: dict, session: AsyncSession):
    return await BalanceDAO.find_one_by_primary_key(session=session, primary_key=Balance_Find_Pydantic(user_id=user_data["user_id"], ticker=user_data["ticker"]))


@connection(isolation_level="SERIALIZABLE", commit=True) 
async def create_order(user_data: dict, session: AsyncSession):
    try:
        user = await get_user(user_data=user_data, session=session)
        if not user:
            return HTTPException(status_code=404, detail="User not found")
        new_order_scheme = Create_Limit_Order_Pydantic(
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
        if new_order_scheme.price == 0: 
            Filter_Model = create_model(
                "Filter_Model",
                ticker=(str, ...),
                direction=(DirectionEnun, ...),
            )
            find_direction = DirectionEnun.SELL if new_order_scheme.direction == DirectionEnun.BUY else DirectionEnun.BUY 
            orders = await OrderDAO.find_available_orders(session=session, filters=Filter_Model(ticker=new_order_scheme.ticker, direction=find_direction))
            if len(orders) < new_order_scheme.qty:
                return {"succes": False}
            else:
                for existed_order in orders:
                    new_order_free_units = new_order.qty - new_order.filled 
                    existed_order_free_units = existed_order.qty - existed_order.filled 
                    if new_order_free_units > existed_order_free_units:
                        transaction_amount = existed_order_free_units
                        new_order.filled += transaction_amount 
                        existed_order.filled += transaction_amount
                    else:
                        transaction_amount = existed_order_free_units - (existed_order_free_units - new_order_free_units)
                        new_order.filled += transaction_amount
                        existed_order.filled += transaction_amount
                    buyer_id = new_order.user_id if new_order.direction == DirectionEnun.BUY else existed_order.user_id
                    seller_id = existed_order.user_id if new_order.direction == DirectionEnun.BUY else new_order.user_id
                    await BalanceDAO.update_balance(session=session, primary_key=Balance_Find_Pydantic(user_id=buyer_id, ticker=new_order.ticker), amount=transaction_amount)
                    await TransactionDAO.add(session=session, values=
                                                    Create_Transaction_Pydantic(
                                                        buyer_id=buyer_id,
                                                        seller_id=seller_id,
                                                        ticker=new_order.ticker,
                                                        amount=transaction_amount,
                                                        price=new_order.price))
                    if new_order.filled == new_order.qty:
                        new_order.status = StatusEnum.EXECUTED
                    else:
                        new_order.status = StatusEnum.PARTIALLY_EXECUTED
                    if existed_order.filled == existed_order.qty:
                        existed_order.status = StatusEnum.EXECUTED
                    else:
                        existed_order.status = StatusEnum.PARTIALLY_EXECUTED
            
        else: 
            new_order = await сreate_limit_order(session, user, new_order_scheme, user_balance)

        await session.flush()
        return {"succes": True, "order_id": new_order.id}
    except SQLAlchemyError as e:
        raise HTTPException(status_code=500, detail=f"Database error {e}")


async def сreate_limit_order(session: AsyncSession, user: User, new_order_scheme: Create_Limit_Order_Pydantic, user_balance: Balance):
    if new_order_scheme.direction == DirectionEnun.SELL and user_balance.amount < new_order_scheme.qty:
        raise HTTPException(405, detail=f"Not enough {new_order_scheme.ticker}")
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
    if orders:
        for existed_order in orders:
            new_order_free_units = new_order.qty - new_order.filled 
            existed_order_free_units = existed_order.qty - existed_order.filled 
            if new_order_free_units > existed_order_free_units:
                transaction_amount = existed_order_free_units
                new_order.filled += transaction_amount 
                existed_order.filled += transaction_amount
            else:
                transaction_amount = existed_order_free_units - (existed_order_free_units - new_order_free_units)
                new_order.filled += transaction_amount
                existed_order.filled += transaction_amount
            buyer_id = new_order.user_id if new_order.direction == DirectionEnun.BUY else existed_order.user_id
            seller_id = existed_order.user_id if new_order.direction == DirectionEnun.BUY else new_order.user_id
            await BalanceDAO.update_balance(session=session, primary_key=Balance_Find_Pydantic(user_id=buyer_id, ticker=new_order.ticker), amount=transaction_amount)
            await TransactionDAO.add(session=session, values=
                                            Create_Transaction_Pydantic(
                                                buyer_id=buyer_id,
                                                seller_id=seller_id,
                                                ticker=new_order.ticker,
                                                amount=transaction_amount,
                                                price=new_order.price))
            if new_order.filled == new_order.qty:
                new_order.status = StatusEnum.EXECUTED
            else:
                new_order.status = StatusEnum.PARTIALLY_EXECUTED
            if existed_order.filled == existed_order.qty:
                existed_order.status = StatusEnum.EXECUTED
            else:
                existed_order.status = StatusEnum.PARTIALLY_EXECUTED
    return new_order


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
    if not user:
        raise HTTPException(status_code=404)
    Filter_Model = create_model(
        "Filter_model",
        id = (str, ...),
        user_id = (str, ...)
    )
    order = await OrderDAO.find_one_or_none(session=session, filters=Filter_Model(id = user_data["order_id"], user_id=user.id))
    if not order:
        raise HTTPException(status_code=404)
    balance = await BalanceDAO.find_one_by_primary_key(session=session, primary_key=Balance_Find_Pydantic(user_id=user.id, ticker=order.ticker))
    if not balance:
        raise HTTPException(status_code=404)
    if order.status == StatusEnum.NEW and order.direction == DirectionEnun.SELL:
        balance.amount += order.qty
    elif order.status == StatusEnum.PARTIALLY_EXECUTED and order.direction == DirectionEnun.SELL:
        balance.amount += order.qty - order.filled
    order.status = StatusEnum.CANCELLED
    
    return {"succes": True}

    