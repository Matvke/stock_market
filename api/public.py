from fastapi import APIRouter
from typing import List

from dependencies import DbDep
from schemas.request import NewUserRequest, OrderbookRequest
from schemas.response import UserResponse, InstrumentResponse, L2OrderBook
from services.public import register_user, get_instruments_list, get_orderbook
from misc.enums import DirectionEnun


router = APIRouter(prefix="/api/v1/public")

@router.post("/register", response_model=UserResponse)
async def api_register_user(
    new_user: NewUserRequest,
    session: DbDep
):
    return await register_user(new_user, session)


@router.get("/instrument", response_model=List[InstrumentResponse])
async def api_get_instruments(session: DbDep):
    return await get_instruments_list(session)


@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
async def api_get_orderbook(session: DbDep, ticker: str, limit: int = 10):
    bid_levels = await get_orderbook(session, OrderbookRequest(ticker=ticker, direction=DirectionEnun.BUY), limit)
    ask_levels = await get_orderbook(session, OrderbookRequest(ticker=ticker, direction=DirectionEnun.SELL), limit)

    return L2OrderBook(bid_levels=bid_levels, ask_levels=ask_levels)