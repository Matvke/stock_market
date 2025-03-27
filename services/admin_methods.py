from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from dao.session_maker import connection
from dao.dao import BalanceDAO, UserDAO, InstrumentDAO
from misc.enums import RoleEnum
from pydantic import create_model
from old_schemas import *
from public_methods import get_user


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
        raise HTTPException(status_code=403)
    else:
        await InstrumentDAO.delete_by_filters(session=session, primary_key=Primary_Key_Model(ticker=user_data["ticker"]))
        return {'succes': True}
    

@connection(isolation_level="SERIALIZABLE", commit=True)
async def delete_user(user_data: dict, session: AsyncSession):
    user = await get_user(session=session, user_data=user_data)
    if user.role != RoleEnum.ADMIN: # NoneType error
        raise HTTPException(status_code=403)
    await UserDAO.delete_one_by_primary_key(session=session, primary_key=Id_Item_Pydantic(id = user_data["user_id"]))
    return user


@connection(isolation_level="SERIALIZABLE", commit=True)
async def admin_balance_update(user_data: dict, session: AsyncSession):
    user = await UserDAO.find_one_by_primary_key(session=session, primary_key=Id_Item_Pydantic(id = user_data["user_id"]))
    if user:
        amount = user_data["amount"]
        return await BalanceDAO.update_balance(session=session, primary_key=Balance_Find_Pydantic(user_id=user.id, ticker=user_data["ticker"]), amount=amount)
    else:
        raise HTTPException(status_code=404)
