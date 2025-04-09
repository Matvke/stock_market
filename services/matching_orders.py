from sqlalchemy.ext.asyncio import AsyncSession
from dao.dao import OrderDAO
from dao.base import Base
from misc.db_models import Order


async def matching_orders(session: AsyncSession, new_order: Order):
    pass