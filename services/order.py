import logging
from uuid import UUID
from schemas.response import OkResponse, CreateOrderResponse, MarketOrderResponse, LimitOrderResponse, convert_order
from schemas.request import OrderRequest, LimitOrderRequest, MarketOrderRequest, BalanceRequest
from schemas.create import LimitOrderCreate, MarketOrderCreate
from typing import List
from misc.enums import DirectionEnum, OrderEnum, StatusEnum
from dao.dao import OrderDAO, BalanceDAO
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from services.engine import matching_engine
from services.trade_execution import trade_executor


async def create_market_order(session: AsyncSession, user_id: UUID, order_data: MarketOrderRequest) -> CreateOrderResponse:
    async with session.begin():
        search_ticker = order_data.ticker if order_data.direction == DirectionEnum.SELL else "RUB"
        user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=search_ticker))

        if not user_balance:
            raise HTTPException(400, f"Balance {search_ticker} not found")
        
        market_order = await OrderDAO.add(
            session,
            MarketOrderCreate(
                user_id=user_id,
                direction=order_data.direction,
                ticker=order_data.ticker,
                qty=order_data.qty,
                order_type=OrderEnum.MARKET
            ))

        executions = matching_engine.add_market_order(order=market_order, balance=user_balance.amount)
        # Сортируем по buyer_id и seller_id для минимизации deadlocks
        sorted_executions = sorted(
            executions,
            key=lambda x: (x.bid_order.user_id, x.ask_order.user_id)
        )

        if not executions:
            logging.info("Order execution failed. Not enough funds or orders in orderbook")
            raise HTTPException(400, "Order execution failed. Not enough funds or orders in orderbook") 
        
        await trade_executor.execute_trade(session, sorted_executions)
        
        if market_order.status != StatusEnum.EXECUTED or market_order.filled != market_order.qty:
            logging.error(f"Ошибка в маркет ордере. {market_order.filled, market_order.status}") # TODO Все равно до сюда доходит. Не должно. Рассинхрон.
            raise HTTPException(500, "Чет я не понимаю") 
            
        return CreateOrderResponse(success=True, order_id=market_order.id)


async def create_limit_order(session: AsyncSession, user_id: UUID, order_data: LimitOrderRequest) -> CreateOrderResponse:
    async with session.begin():
        # Продавец резервирует в ордер токены, которые он хочет продать
        if order_data.direction == DirectionEnum.SELL:
            user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=order_data.ticker))
            if not user_balance or user_balance.amount < order_data.qty:
                raise HTTPException(400, f"Not enough {order_data.ticker}")
            else:
                user_balance.amount -= order_data.qty
        # Покупатель резервирует в ордер рубли, на сумму которых он хочет купить 
        else:
            user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker="RUB"))
            if user_balance.amount < order_data.qty * order_data.price:
                raise HTTPException(400, "Not enough RUB")
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
        matching_engine.add_limit_order(limit_order)
        return CreateOrderResponse(success=True, order_id=limit_order.id)


async def get_list_orders(session: AsyncSession, user_id: UUID) -> List[MarketOrderResponse | LimitOrderResponse]:
    orders = await OrderDAO.find_all(session, OrderRequest(user_id=user_id))
    logging.info(f"Запрошен лист ордеров для {user_id}: {len(orders)}")
    if not orders:
        return []
    return [convert_order(o) for o in orders]


async def get_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> MarketOrderResponse | LimitOrderResponse:
    order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
    logging.info(f"Запрошен ордер для {user_id}: {order_id}")
    if not order:
        raise HTTPException(404, "Order not found")
    return convert_order(order)


async def cancel_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> OkResponse:
    async with session.begin():
        order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
        if not order: 
            raise HTTPException(400, 'Order not found.')
        
        elif order.status == StatusEnum.CANCELLED or order.status == StatusEnum.EXECUTED or order.status == StatusEnum.PARTIALLY_EXECUTED:
            raise HTTPException(400, 'You cannot cancel an executed or canceled order')
        
        elif not matching_engine.cancel_order(order):
            logging.error("Рассинхрон БД и движка.") # TODO Выходит такая ошибка => Рассинхрон бд и matching engine. БЛЯТЬ ОНА РЕАЛЬНО ВЫХОДИТ
            raise HTTPException(500, 'Order not found in orderbook.') 
        
        elif order.direction == DirectionEnum.SELL:
            balance_in_tocken = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=order.ticker))
            balance_in_tocken.amount += order.qty - order.filled

        elif order.order_type == OrderEnum.MARKET:
            raise HTTPException(400, 'You cannot cancel a market order.')
        else: 
            balance_in_rub = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker="RUB"))
            balance_in_rub.amount += (order.qty - order.filled) * order.price 
        order.status = StatusEnum.CANCELLED

        return OkResponse(success=True)
