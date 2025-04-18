from sqlalchemy.ext.asyncio import AsyncSession
from schemas.response import UserResponse, OkResponse
from schemas.request import InstrumentRequest, DepositRequest, IdRequest, TickerRequest, BalanceRequest, WithdrawRequest
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO
from uuid import UUID
from misc.enums import VisibilityEnum
from services.engine import matching_engine


async def delete_user(session: AsyncSession, user_id: UUID) -> UserResponse:
    async with session.begin_nested():
        user = await UserDAO.find_one_by_primary_key(session, IdRequest(id=user_id))
        user.visibility = VisibilityEnum.DELETED
        return UserResponse.model_validate(user)


async def add_instrument(session: AsyncSession, instrument_data: InstrumentRequest) -> OkResponse:
    async with session.begin_nested():
        new_instrument = await InstrumentDAO.add(session, instrument_data)
        matching_engine.add_instrument(new_instrument)
        return OkResponse()


async def delete_instrument(session: AsyncSession, ticker: str) -> OkResponse:
    async with session.begin_nested():
        instrument = await InstrumentDAO.find_one_by_primary_key(session, TickerRequest(ticker=ticker))
        matching_engine.remove_orderbook(ticker=instrument.ticker)
        instrument.visibility = VisibilityEnum.DELETED
        return OkResponse()


async def update_balance(session: AsyncSession, body: DepositRequest | WithdrawRequest) -> OkResponse:
    async with session.begin_nested():
        amount = -body.amount if isinstance(body, WithdrawRequest) else body.amount
        await BalanceDAO.update_balance(session, BalanceRequest(user_id=body.user_id, ticker=body.ticker), amount=amount)
        return OkResponse()