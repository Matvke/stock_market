from fastapi import APIRouter
from dependencies import DbDep, CurrentAdmin
from uuid import UUID
from schemas.response import UserResponse, OkResponse
from schemas.request import InstrumentRequest, DepositRequest, WithdrawRequest
from services.admin import delete_user, add_instrument, delete_instrument, update_balance


admin_router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@admin_router.delete("/user/{user_id}", response_model=UserResponse)
async def api_delete_user(user: CurrentAdmin, session: DbDep, user_id: UUID) -> UserResponse:
    return await delete_user(session=session, user_id=user_id)


@admin_router.post("/instrument", response_model=OkResponse)
async def api_create_instrument(user: CurrentAdmin, session: DbDep, instrument_data: InstrumentRequest) -> OkResponse:
    return await add_instrument(session, instrument_data)


@admin_router.delete("/instrument/{ticker}", response_model=OkResponse)
async def api_delete_instrument(user: CurrentAdmin, session: DbDep, ticker: str) -> OkResponse:
    return await delete_instrument(session, ticker)


@admin_router.post("/balance/deposit", response_model=OkResponse)
async def api_deposit(user: CurrentAdmin, session: DbDep, body: DepositRequest) -> OkResponse:
    return await update_balance(session, body)


@admin_router.post("/balance/withdraw", response_model=OkResponse)
async def api_withdraw(user: CurrentAdmin, session: DbDep, body: WithdrawRequest) -> OkResponse:
    return await update_balance(session, body)
