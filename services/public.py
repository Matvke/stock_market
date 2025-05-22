from schemas.response import UserResponse, InstrumentResponse, TransactionResponse, L2OrderBook
from schemas.request import NewUserRequest, TransactionRequest
from schemas.create import UserCreate, BalanceCreate
from dao.dao import UserDAO, InstrumentDAO, TransactionDAO, BalanceDAO
from uuid import uuid4
from misc.enums import RoleEnum
from misc.db_models import Instrument
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from services.engine import matching_engine
import logging


async def register_user(new_user_model: NewUserRequest, session: AsyncSession) -> UserResponse:
    user_model = UserCreate(
        name=new_user_model.name,
        role=RoleEnum.USER,
        api_key=f"key-{uuid4()}"
    )
    async with session.begin():
        user = await UserDAO.add(session, user_model)
        await BalanceDAO.add(session, BalanceCreate(user_id=user.id, ticker='RUB'))
        logging.info(f"Added new user {user.name} {user.id}")
        return UserResponse.model_validate(user)


async def get_instruments_list(session: AsyncSession) -> List[Instrument] | None:
    instruments = await InstrumentDAO.find_all(session=session)
    if not instruments:
        return []
    return [InstrumentResponse.model_validate(instrument) for instrument in instruments]


async def get_orderbook(ticker: str, limit: int) -> L2OrderBook:
    return matching_engine.get_orderbook(ticker, limit)
    

async def get_transactions_history(session: AsyncSession, filter_model: TransactionRequest, limit: int = 10) -> List[TransactionResponse]:
    transactions = await TransactionDAO.find_all(session, filter_model)
    logging.info("Transaction history requested")
    if not transactions: 
        return []
    return [TransactionResponse.model_validate(t) for t in transactions]