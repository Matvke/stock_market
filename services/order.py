from misc.db_models import *
from misc.internal_classes import InternalOrder
from schemas.response import OkResponse, CreateOrderResponse, MarketOrderResponse, LimitOrderResponse, convert_order
from schemas.request import OrderRequest, LimitOrderRequest, MarketOrderRequest, BalanceRequest
from schemas.create import LimitOrderCreate, MarketOrderCreate, CancelOrderCreate
from typing import List
from misc.enums import DirectionEnum
from dao.dao import OrderDAO, BalanceDAO
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from services.engine import matching_engine


async def create_market_order(session: AsyncSession, user_id: UUID, order_data: MarketOrderRequest) -> CreateOrderResponse:
    # Находим тикер, баланс которого будет списан: если покупаем, то списываем с рублевого счета, иначе с токенового счета.
    search_ticker = order_data.ticker if order_data.direction == DirectionEnum.SELL else "RUB"
    # Находим баланс пользователя.
    user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=search_ticker))
    if not user_balance:
        raise HTTPException(404, f"Balance {search_ticker} not found")
    
    # Получаем ордера с противоположной части стакана
    if order_data.direction == DirectionEnum.BUY:
        book = await matching_engine.get_asks_from_book(order_data.ticker)
    else:
        book = await matching_engine.get_bids_from_book(order_data.ticker)
    
    if can_execute_market_order(
        order_qty=order_data.qty, 
        direction=order_data.direction,
        book_orders=book,
        user_balance=user_balance):
    
        async with session.begin_nested():
            market_order = await OrderDAO.add(
                session,
                MarketOrderCreate(
                    user_id=user_id,
                    direction=order_data.direction,
                    ticker=order_data.ticker,
                    qty=order_data.qty,
                    order_type=OrderEnum.MARKET
                ))

            output = await matching_engine.add_order(session=session, order=market_order)
        
            if not output:
                raise HTTPException(500, "Unexpected error: ВИДИШЬ ЭТУ ОШИБКУ, ЗНАЧИТ КАПЕЦ!!!")
            if market_order.status == StatusEnum.EXECUTED:
                return CreateOrderResponse(success=True, order_id=market_order.id)


async def create_limit_order(session: AsyncSession, user_id: UUID, order_data: LimitOrderRequest) -> CreateOrderResponse:
    async with session.begin_nested():
        # Продавец резервирует в ордер токены, которые он хочет продать
        if order_data.direction == DirectionEnum.SELL:
            user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=order_data.ticker))
            if user_balance.amount < order_data.qty:
                raise HTTPException(400, f"Not enough {order_data.ticker}")
            else:
                user_balance.amount -= order_data.qty
        # Покупатель резервирует в ордер рубли, на сумму которых он хочет купить 
        else:
            user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker="RUB"))
            if user_balance.amount < order_data.qty * order_data.price:
                raise HTTPException(400, f"Not enough RUB")
            else:
                user_balance.amount -= order_data.qty * order_data.price
        limit_order = await OrderDAO.add(session, 
                                    LimitOrderCreate(
                                        user_id=user_id,
                                        direction=order_data.direction,
                                        ticker=order_data.ticker,
                                        qty=order_data.qty,
                                        price=order_data.price
                                    ))
        await matching_engine.add_order(session, limit_order)
        return CreateOrderResponse(success=True, order_id=limit_order.id)


async def get_list_orders(session: AsyncSession, user_id: UUID) -> List[MarketOrderResponse | LimitOrderResponse]:
    orders = await OrderDAO.find_all(session, OrderRequest(user_id=user_id))
    return [convert_order(o) for o in orders]


async def get_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> MarketOrderResponse | LimitOrderResponse:
    order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
    return convert_order(order)


async def cancel_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> OkResponse:
    async with session.begin_nested():
        order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
        if not order: 
            raise HTTPException(400, 'Order not found.')
        
        if order.status == StatusEnum.CANCELLED or order.status == StatusEnum.EXECUTED:
            raise HTTPException(400, 'You cannot cancel an executed or canceled order')
        
        if not matching_engine.cancel_order(order):
            raise HTTPException(400, 'Order not found in orderbook.') 
        
        if order.direction == DirectionEnum.SELL:
            balance_in_tocken = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=order.ticker))
            balance_in_tocken.amount += order.qty - order.filled

        else: 
            balance_in_rub = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker="RUB"))
            balance_in_rub.amount += (order.qty - order.filled) * order.price 
        order.status = StatusEnum.CANCELLED

        return OkResponse(success=True)

    

def can_execute_market_order(
    order_qty: int,
    direction: DirectionEnum,
    book_orders: list[InternalOrder],
    user_balance: Balance
) -> bool:
    remaining_qty = order_qty
    total_cost = 0.0  # сколько РУБЛЕЙ потратим или получим
    available_qty = 0  # сколько токенов доступно в стакане

    for order in book_orders:
        if remaining_qty <= 0:
            break

        trade_qty = min(order.remaining, remaining_qty)
        available_qty += trade_qty
        total_cost += trade_qty * order.price
        remaining_qty -= trade_qty

    # Недостаточно ордеров на нужное кол-во
    if available_qty < order_qty:
        raise HTTPException(400, detail="Not enough applications in orderbook")

    if direction == DirectionEnum.BUY:
        # Нужно достаточно РУБЛЕЙ, чтобы купить
        if user_balance.amount < total_cost:
            raise HTTPException(400, detail="Not enough rubles to buy")
    else:  # SELL
        # Нужно достаточно самих токенов
        if user_balance.amount < order_qty:
            raise HTTPException(400, detail="Not enough tokens for sale")

    return True