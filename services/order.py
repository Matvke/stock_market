from misc.db_models import *
from schemas.response import OkResponse, CreateOrderResponse, MarketOrderResponse, LimitOrderResponse, convert_order
from schemas.request import OrderRequest, LimitOrderRequest, MarketOrderRequest, BalanceRequest
from schemas.create import LimitOrderCreate, MarketOrderCreate, TransactionCreate
from typing import List
from dao.dao import OrderDAO, BalanceDAO, TransactionDAO
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from services.matching_orders import matching_orders


async def create_market_order(session: AsyncSession, user_id: UUID, order_data: MarketOrderRequest) -> CreateOrderResponse:
    try:
        # Находим тикер, баланс которого будет списан: если покупаем, то списываем с рублевого счета, иначе с токенового счета.
        search_ticker = order_data.ticker if order_data.direction == DirectionEnun.SELL else "RUB"
        # Находим баланс пользователя.
        # Открываем транзакцию
        user_balance = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=search_ticker))
        if not user_balance:
            raise HTTPException(404, f"Balance {search_ticker} not found")
        # Доступные ордера - это ордера не от зачинщика заявки (чтоб не проводить сделку с собой), 
        # с тем же тикером, новые или частично исполненные и с противоположным направлением.
        available_orders = await OrderDAO.get_available_orders(session, order_data.ticker, user_id, order_data.direction)
        # Посчитаем колчество свободных единиц токена на рынке. Если их недостаточно, ордер нужно отклонить. 
        available_units = 0
        available_units_price = 0
        for order in available_orders:
            # Считаем сколько в доступном ордере свободных единиц и их цену: 
            # Общее количество закупок/продаж - исполненные закупки/продажи.
            available_units += (order.qty - order.filled)
            available_units_price += order.price * (order.qty - order.filled)
        if order_data.qty > available_units: 
            raise HTTPException(400, "Order denied. Not enough applications")
        if user_balance.amount < order_data.qty:
            raise HTTPException(400, f"Order denied. Not enough {search_ticker}")
        # Заявок на рынке достаточно, можно создавать ордер.
        new_order = await OrderDAO.add(session, 
                            MarketOrderCreate(
                                user_id=user_id, 
                                direction=order_data.direction, 
                                ticker=order_data.ticker,
                                qty=order_data.qty
                                ))
        # Сразу после создания ордера сопоставляем ордера и проводим транзакции
        await matching_order(session, available_orders, new_order)
        await session.commit()
        return CreateOrderResponse(success=True, order_id=new_order.id)
    except Exception as e:
        await session.rollback()
        raise e


async def matching_order(session: AsyncSession, available_orders: list[Order], new_order: Order):
    for existed_order in available_orders:
        # Считаем количество свободных единиц с обоих сторон.
        new_order_free_units = new_order.qty - new_order.filled 
        existed_order_free_units = existed_order.qty - existed_order.filled 
        # Считаем количество токенов, которые нужно перевести.
        transaction_amount = existed_order_free_units if new_order_free_units > existed_order_free_units else existed_order_free_units - (existed_order_free_units - new_order_free_units)

        # Узнаем кто покупает, кто продает.
        if new_order.direction == DirectionEnun.BUY:
            buyer_id = new_order.user_id
            seller_id = existed_order.user_id
        else:
            buyer_id = existed_order.user_id
            seller_id = new_order.user_id

        await execute_transaction(session, new_order, existed_order, transaction_amount, buyer_id, seller_id)
        
        # Меняем статус нового ордера
        if existed_order.filled == existed_order.qty:
            existed_order.status = StatusEnum.EXECUTED
        else:
            existed_order.status = StatusEnum.PARTIALLY_EXECUTED
        # Если новый ордер исполнен, надо его закрыть, поставив статус EXECUTED и выйти из цикла
        if new_order.filled == new_order.qty:
            new_order.status = StatusEnum.EXECUTED
            break
        else:
            # Либо если он закрыт не полностью продолжить 
            new_order.status = StatusEnum.PARTIALLY_EXECUTED



async def execute_transaction(session: AsyncSession, new_order: Order, existed_order: Order, transaction_amount: int, buyer_id: UUID, seller_id: UUID):
    # Списываем рубли со счета ордера
    # Списываем токены у продавца со счета ордера
    new_order.filled += transaction_amount 
    existed_order.filled += transaction_amount

    # Переводим рубли продавцу
    seller_balance_in_rub = await BalanceDAO.update_balance(session, BalanceRequest(user_id=seller_id, ticker="RUB"), transaction_amount * existed_order.price)
    # Пополняем баланс покупателя на новую валюту (Если баланс еще не создан, он создастся автоматически).
    buyer_balance_in_tocken = await BalanceDAO.update_balance(session, BalanceRequest(user_id=buyer_id, ticker=new_order.ticker), transaction_amount)
    # Сохраняем транзакцию перевода токенов
    transaction = await TransactionDAO.add(session, TransactionCreate(
                buyer_id=buyer_id, 
                seller_id=seller_id,
                ticker=new_order.ticker,
                amount=transaction_amount,
                price=existed_order.price))
    # Сохраняем транзакцию перевода рублей
    transaction = await TransactionDAO.add(session, TransactionCreate(
                buyer_id=seller_id, 
                seller_id=buyer_id,
                ticker="RUB",
                amount=transaction_amount,
                price=existed_order.price))


async def create_limit_order(session: AsyncSession, user_id: UUID, order_data: LimitOrderRequest) -> CreateOrderResponse:
    try:
        # Продавец резервирует в ордер токены, которые он хочет продать
        if order_data.direction == DirectionEnun.SELL:
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
        new_order = await OrderDAO.add(session, 
                                    LimitOrderCreate(
                                        user_id=user_id,
                                        direction=order_data.direction,
                                        ticker=order_data.ticker,
                                        qty=order_data.qty,
                                        price=order_data.price
                                    ))
        await session.commit()
        return CreateOrderResponse(success=True, order_id=new_order.id)
    except Exception as e:
        await session.rollback()
        raise e


async def get_list_orders(session: AsyncSession, user_id: UUID) -> List[MarketOrderResponse | LimitOrderResponse]:
    orders = await OrderDAO.find_all(session, OrderRequest(user_id=user_id))
    return [convert_order(o) for o in orders]


async def get_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> MarketOrderResponse | LimitOrderResponse:
    order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
    return convert_order(order)


async def cancel_order(session: AsyncSession, user_id: UUID, order_id: UUID) -> OkResponse:
    try:
        order = await OrderDAO.find_one_or_none(session, OrderRequest(id=order_id, user_id=user_id))
        if not order: return OkResponse(success=False)
        if order.direction == DirectionEnun.SELL:
            balance_in_tocken = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker=order.ticker))
            balance_in_tocken.amount += order.qty - order.filled
        else: 
            balance_in_rub = await BalanceDAO.find_one_by_primary_key(session, BalanceRequest(user_id=user_id, ticker="RUB"))
            balance_in_rub.amount += (order.qty - order.filled) * order.price 
        order.status = StatusEnum.CANCELLED
        await session.commit()
        return OkResponse(success=True)
    except Exception as e:
        await session.rollback()
        raise e