from fastapi import APIRouter
from dependencies import DbDep, CurrentUser
from schemas.response import CreateOrderResponse, OkResponse, MarketOrderResponse, LimitOrderResponse
from schemas.request import LimitOrderRequest, MarketOrderRequest
from typing import List
from services.order import get_order, get_list_orders, create_market_order, create_limit_order, cancel_order
from pydantic import UUID4


order_router = APIRouter(prefix="/api/v1/order", tags=['order'])

@order_router.post("", response_model=CreateOrderResponse)
async def api_create_order(
    order_data: LimitOrderRequest | MarketOrderRequest,
    user: CurrentUser, 
    session: DbDep):
    if hasattr(order_data, 'price'):
        return await create_limit_order(session, user.id, order_data)
    return await create_market_order(session, user.id, order_data)


@order_router.get("", response_model=List[MarketOrderResponse | LimitOrderResponse])
async def api_get_list_order(user: CurrentUser, session: DbDep):
    return await get_list_orders(session, user.id)


@order_router.get("/{order_id}", response_model=MarketOrderResponse | LimitOrderResponse)
async def api_get_order(user: CurrentUser, session: DbDep, order_id: UUID4):
    return await get_order(session, user.id, order_id) 


@order_router.delete("/{order_id}", response_model=OkResponse)
async def api_cancel_order(user: CurrentUser, session: DbDep, order_id: UUID4):
    return await cancel_order(session, user.id, order_id)