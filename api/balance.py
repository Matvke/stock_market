from fastapi import APIRouter
from dependencies import DbDep, CurrentUser
from schemas.request import *
from schemas.response import *
from services.balance import get_balances


balance_router = APIRouter(prefix="/api/v1/balance", tags=["balance"])

@balance_router.get("", response_model=BalanceResponse)
async def api_get_balances(
    user: CurrentUser,
    session: DbDep
):
    return await get_balances(session, user.id)

