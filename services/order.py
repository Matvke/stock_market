import asyncio
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
        ticker = order_data.ticker if order_data.direction == DirectionEnum.SELL else "RUB"
        user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=ticker))

        if not user_balance:
            raise HTTPException(400, f"Balance {ticker} not found")
        
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
            logging.info("Order execution failed. Not enough offers")
            raise HTTPException(400, "Order execution failed. Not enough offers") 
        
        # Блокируем средства
        if not (await block_funds(session, user_id, market_order, executions)):
            logging.info(f"Order execution failed. Not enough {ticker}")
            raise HTTPException(400, f"Order execution failed. Not enough {ticker}")

        
        await trade_executor.execute_trade(session, sorted_executions)
        
        if market_order.status != StatusEnum.EXECUTED or market_order.filled != market_order.qty:
            logging.error(f"Ошибка в маркет ордере. {market_order.filled, market_order.status}") 
            raise HTTPException(500, "Desync error") 
            
        return CreateOrderResponse(success=True, order_id=market_order.id)


async def block_funds(session, user_id, market_order, executions) -> bool:
    if market_order.direction == DirectionEnum.BUY:
        required_rub = sum(
                execution.executed_qty * execution.execution_price
                for execution in executions
            )
        return await BalanceDAO.block_balance(session, user_id=user_id, ticker="RUB", amount=required_rub)
    else:
        required_tockens = sum(
                execution.executed_qty
                for execution in executions
            )
        return await BalanceDAO.block_balance(session, user_id=user_id, ticker=market_order.ticker, amount=required_tockens)


async def create_limit_order(session: AsyncSession, user_id: UUID, order_data: LimitOrderRequest) -> CreateOrderResponse:
    async with session.begin():
        # TODO Возможно стоит запускать match_all тут, но не будет ли это очень затратно?
        # Определяем что и скольк тратим
        if order_data.direction == DirectionEnum.SELL:
            ticker = order_data.ticker
            amount = order_data.qty
        else:
            ticker = "RUB"
            amount = order_data.qty * order_data.price

        if not await BalanceDAO.block_balance(session, user_id, ticker, amount):
            raise HTTPException(400, f"Not enough {ticker}. {amount} required.")
        
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
        raise HTTPException(400, "Order not found")
    return convert_order(order)


async def cancel_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> OkResponse:
    async with session.begin():
        order = await OrderDAO.get_order_by_id_with_for_update(session, order_id, user_id)
        if not order:
            raise HTTPException(400, "Order not found.")
        
        if order.order_type == OrderEnum.MARKET:
            raise HTTPException(400, 'You cannot cancel a market order.')
        
        if order.status == StatusEnum.EXECUTED or order.status == StatusEnum.CANCELLED:
            raise HTTPException(400, "You cannot cancel executed/canceled order.")
        
        # Попробуем дать время TradeExecutor для обновления БД и закрытия транзакций.
        # Пока что включена блокировка for update в методе get_order_by_id_with_for_update для теста.
        attempts = 3
        while not matching_engine.cancel_order(order):
            if attempts <= 0:
                break
            attempts -= 1
            await asyncio.sleep(0.1)
        else:
            if order.direction == DirectionEnum.BUY:
                ticker = "RUB"
                amount = (order.qty - order.filled) * order.price
            else:
                ticker = order.ticker
                amount = order.qty - order.filled
            if not await BalanceDAO.unblock_balance(session, user_id, ticker, amount):
                raise HTTPException(400, f"Not enough blocked {ticker}.")
            order.status = StatusEnum.CANCELLED

            return OkResponse(success=True)
        
        if not matching_engine.cancel_order(order):
            logging.error(f"Engine and DB out of sync. Order {order.id, order.direction, order.price, order.qty, order.filled, order.status}")
            raise HTTPException(500, "Engine and DB out of sync.") # TODO До сюда доходит


