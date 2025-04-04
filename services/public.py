from misc.db_models import *
from schemas.response import UserResponse, InstrumentResponse, Level, TransactionResponse
from schemas.request import NewUserRequest, OrderbookRequest, TransactionRequest
from schemas.internal import UserCreate
from dao.dao import UserDAO, InstrumentDAO, OrderDAO, TransactionDAO
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List


async def register_user(new_user_model: NewUserRequest, session: AsyncSession) -> UserResponse:
    user_model = UserCreate(
        name=new_user_model.name,
        role=RoleEnum.USER,
        api_key=f"key-{uuid4()}"
    )
    user = await UserDAO.add(session, user_model)
    return UserResponse.model_validate(user)


async def get_instruments_list(session: AsyncSession) -> List[Instrument] | None:
    instruments = await InstrumentDAO.find_all(session=session)
    return [InstrumentResponse.model_validate(instrument) for instrument in instruments]


async def get_orderbook(session: AsyncSession, filter_model: OrderbookRequest, limit: int = 10) -> List[Level]:
    orders = await OrderDAO.find_all(session, filters=filter_model, limit=limit)
    return [Level.model_validate(o) for o in orders]


async def get_transactions_history(session: AsyncSession, filter_model: TransactionRequest, limit: int = 10) -> List[TransactionResponse]:
    transactions = await TransactionDAO.find_all(session, filter_model, limit)
    return [TransactionResponse.model_validate(t) for t in transactions]