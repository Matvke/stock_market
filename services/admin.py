from sqlalchemy.ext.asyncio import AsyncSession
from schemas.response import UserResponse, OkResponse
from schemas.request import InstrumentRequest, DepositRequest, IdRequest, TickerRequest, WithdrawRequest
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO
from uuid import UUID
from misc.enums import VisibilityEnum
from services.engine import matching_engine
import logging
from fastapi.exceptions import HTTPException


async def delete_user(session: AsyncSession, user_id: UUID) -> UserResponse:
    async with session.begin():
        user = await UserDAO.find_one_by_primary_key(session, IdRequest(id=user_id))
        user.visibility = VisibilityEnum.DELETED
        return UserResponse.model_validate(user)


async def add_instrument(session: AsyncSession, instrument_data: InstrumentRequest) -> OkResponse:
    async with session.begin():
        instrument_in_db = await check_existed(session, ticker=instrument_data.ticker)
        if instrument_in_db and instrument_in_db.visibility == VisibilityEnum.DELETED:
            instrument_in_db.visibility = VisibilityEnum.ACTIVE
            matching_engine.add_instrument(instrument_in_db)

        elif instrument_in_db and instrument_in_db.visibility == VisibilityEnum.ACTIVE:
            raise HTTPException(400, f"Instrument with ticker = {instrument_data.ticker} already existed.")
        else:
            new_instrument = await InstrumentDAO.add(session, instrument_data)
            matching_engine.add_instrument(new_instrument)
            
        return OkResponse()


async def delete_instrument(session: AsyncSession, ticker: str) -> OkResponse:
    async with session.begin():
        instrument_in_db = await check_existed(session, ticker=ticker)
        if instrument_in_db and instrument_in_db.visibility == VisibilityEnum.ACTIVE:
            # instrument_in_db.visibility = VisibilityEnum.DELETED
            await session.delete(instrument_in_db)
            matching_engine.remove_orderbook(ticker=instrument_in_db.ticker)

        elif instrument_in_db and instrument_in_db.visibility == VisibilityEnum.DELETED:
            raise HTTPException(400, f"Instrument with ticker = {ticker} not existed.")
        
        elif not instrument_in_db:
            raise HTTPException(400, f"Instrument with ticker = {ticker} not existed.")
        return OkResponse()


async def check_existed(session: AsyncSession, ticker: str):
    instrument = await InstrumentDAO.find_existed(session=session, filters=TickerRequest(ticker=ticker))
    if instrument:
        return instrument
    return None


async def update_balance(session: AsyncSession, body: DepositRequest | WithdrawRequest) -> OkResponse:
    async with session.begin():
        amount = -body.amount if isinstance(body, WithdrawRequest) else body.amount
        await BalanceDAO.upsert_balance(session, user_id=body.user_id, ticker=body.ticker, amount=amount)
        logging.info(f"Updated user {body.user_id} balance {body.ticker} to {amount} by admin.")
        return OkResponse()