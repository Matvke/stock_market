from fastapi import APIRouter
from typing import List
from dependencies import DbDep
from schemas.request import NewUserRequest, TransactionRequest
from schemas.response import UserResponse, InstrumentResponse, L2OrderBook, TransactionResponse
from services.public import register_user, get_instruments_list, get_transactions_history, get_orderbook


public_router = APIRouter(prefix="/api/v1/public", tags=['public'])

@public_router.post("/register", response_model=UserResponse)
async def api_register_user(
    new_user: NewUserRequest,
    session: DbDep
):
    return await register_user(new_user, session)


@public_router.get("/instrument", response_model=List[InstrumentResponse])
async def api_get_instruments(session: DbDep):
    return await get_instruments_list(session)


@public_router.get("/orderbook/{ticker}", response_model=L2OrderBook)
async def api_get_orderbook(session: DbDep, ticker: str, limit: int = 10):
    return await get_orderbook(ticker=ticker, limit=limit)


@public_router.get("/transactions/{ticker}", response_model=List[TransactionResponse])
async def api_get_transaction_history(session:DbDep, ticker: str, limit: int = 10):
    return await get_transactions_history(session, TransactionRequest(ticker=ticker), limit)