from schemas.response import BalanceResponse
from typing import List
from dao.dao import BalanceDAO
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID


async def get_balances(session: AsyncSession, user_id: UUID) -> List[BalanceResponse]:
    balances = await BalanceDAO.get_user_balances(session, user_id)
    return BalanceResponse(balances)