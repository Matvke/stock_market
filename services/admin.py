from sqlalchemy.ext.asyncio import AsyncSession
from schemas.response import UserResponse, OkResponse
from schemas.request import InstrumentRequest, DepositRequest, IdRequest, TickerRequest, BalanceRequest, WithdrawRequest
from dao.dao import UserDAO, InstrumentDAO, BalanceDAO
from uuid import UUID
from misc.enums import VisibilityEnum


async def delete_user(session: AsyncSession, user_id: UUID) -> UserResponse:
    try:
        user = await UserDAO.find_one_by_primary_key(session, IdRequest(id=user_id))
        user.visibility = VisibilityEnum.DELETED
        await session.commit()
        return UserResponse.model_validate(user)
    except Exception as e:
        await session.rollback()
        raise e


async def add_instrument(session: AsyncSession, instrument_data: InstrumentRequest) -> OkResponse:
    try:
        new_instrument = await InstrumentDAO.add(session, instrument_data)
        await session.commit()
        return OkResponse()
    except Exception as e:
        await session.rollback()
        raise e


async def delete_instrument(session: AsyncSession, ticker: str) -> OkResponse:
    try:
        instrument = await InstrumentDAO.find_one_by_primary_key(session, TickerRequest(ticker=ticker))
        instrument.visibility = VisibilityEnum.DELETED
        await session.commit()
        return OkResponse()
    except Exception as e:
        await session.rollback()
        raise e


async def update_balance(session: AsyncSession, body: DepositRequest | WithdrawRequest) -> OkResponse:
    try:
        amount = -body.amount if isinstance(body, WithdrawRequest) else body.amount
        await BalanceDAO.update_balance(session, BalanceRequest(user_id=body.user_id, ticker=body.ticker), amount=amount)
        await session.commit()
        return OkResponse()
    except Exception as e:
        await session.rollback()
        raise e

