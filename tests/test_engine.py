import pytest
from sqlalchemy import text
from dao.dao import OrderDAO, BalanceDAO, TransactionDAO, InstrumentDAO
from schemas.create import MarketOrderCreate, LimitOrderCreate, CancelOrderCreate 
from schemas.request import BalanceRequest, IdRequest, InstrumentRequest
from misc.enums import DirectionEnum, StatusEnum, OrderEnum
from services.orderbook import OrderBook
from services.matching import MatchingEngine, run_matching_engine


@pytest.mark.asyncio
async def test_succesfull_add_limit_order_to_orderbook(test_session, test_instruments, test_users, test_orders, filled_test_db):
    ticker = test_instruments[0]['ticker']
    test_orderbook = OrderBook(ticker)
    test_order = await OrderDAO.add(test_session, LimitOrderCreate.model_validate(test_orders[0]))
    trade_list = test_orderbook.add_order(test_order)
    assert len(trade_list) == 0 
    assert len(test_orderbook.get_bids()) == 1


@pytest.mark.asyncio
async def test_succesfull_cancel_limit_order_from_orderbook(test_session, test_instruments, test_users, filled_test_db, test_orders):
    ticker = test_instruments[0]['ticker']
    test_orderbook = OrderBook(ticker)
    test_order = await OrderDAO.add(test_session, LimitOrderCreate.model_validate(test_orders[0]))
    add_trade_list = test_orderbook.add_order(test_order)
    assert len(add_trade_list) == 0
    assert len(test_orderbook.get_bids()) == 1

    cancel_trade_list = test_orderbook.cancel_order(cancel_order=test_order)
    assert cancel_trade_list
    assert len(test_orderbook.get_bids()) == 0


@pytest.mark.asyncio
async def test_succesfull_trade_orderbook(test_session, test_instruments, test_users, filled_test_db, test_orders):
    ticker = test_instruments[0]['ticker']
    test_orderbook = OrderBook(ticker)
    buy_order = await OrderDAO.add(test_session, LimitOrderCreate(
        user_id=test_users[0]['id'],
        direction=DirectionEnum.BUY,
        ticker=ticker,
        qty=3,
        price=20
    ))
    add_trade_list = test_orderbook.add_order(buy_order)
    assert len(add_trade_list) == 0
    assert len(test_orderbook.get_bids()) == 1
    assert len(test_orderbook.get_asks()) == 0

    sell_order1 = await OrderDAO.add(test_session, LimitOrderCreate(
        user_id=test_users[1]['id'],
        direction=DirectionEnum.SELL,
        ticker=ticker,
        qty=3, # Должен частично исполниться
        price=15 # Сдача 5
    ))
    add_trade_list = test_orderbook.add_order(sell_order1)
    assert len(add_trade_list) == 0
    assert len(test_orderbook.get_bids()) == 1
    assert len(test_orderbook.get_asks()) == 1

    # исполнится первый, из-за низкой цены
    sell_order2 = await OrderDAO.add(test_session, LimitOrderCreate(
        user_id=test_users[1]['id'],
        direction=DirectionEnum.SELL,
        ticker=ticker,
        qty=2, # Должен полностью исполниться
        price=10 # Сдача 10 руб * 2 (две сделки) 
    ))
    add_trade_list = test_orderbook.add_order(sell_order2)
    assert len(add_trade_list) == 0
    assert len(test_orderbook.get_bids()) == 1
    assert len(test_orderbook.get_asks()) == 2

    trades = test_orderbook.matching_orders()

    assert len(trades) == 2
    assert len(test_orderbook.get_bids()) == 0
    assert len(test_orderbook.get_asks()) == 1

    assert test_orderbook.get_asks()[0].status == StatusEnum.PARTIALLY_EXECUTED
    assert test_orderbook.get_asks()[0].id == sell_order1.id

    # Проверка 1 сделки с sell_order2, который исполнится полностью
    assert trades[0].bid_order.id == buy_order.id
    assert trades[0].ask_order.id == sell_order2.id
    assert trades[0].executed_qty == sell_order2.qty
    assert trades[0].execution_price == sell_order2.price
    assert trades[0].bid_order_change == (buy_order.price - sell_order2.price) * sell_order2.qty
    assert trades[0].ask_order.filled == sell_order2.qty 
    assert trades[0].ask_order.status == StatusEnum.EXECUTED
    assert trades[0].bid_order.filled == sell_order2.qty 
    assert trades[0].bid_order.status == StatusEnum.PARTIALLY_EXECUTED

    # Проверка 2 сделки с sell_order1, который частично исполнится, а buy_order полностью исполнится
    assert trades[1].bid_order.id == buy_order.id
    assert trades[1].ask_order.id == sell_order1.id
    assert trades[1].executed_qty == 1
    assert trades[1].execution_price == sell_order1.price
    assert trades[1].bid_order_change == (buy_order.price - sell_order1.price) * 1
    assert trades[1].ask_order.filled == 1
    assert trades[1].ask_order.status == StatusEnum.PARTIALLY_EXECUTED
    assert trades[1].bid_order.filled == 3
    assert trades[1].bid_order.status == StatusEnum.EXECUTED


@pytest.mark.asyncio
async def test_succesfull_market_order_orderbook(test_session, test_instruments, test_users, filled_test_db, test_orders):
    ticker = test_instruments[0]['ticker']
    test_orderbook = OrderBook(ticker)

    limit_order = await OrderDAO.add(test_session, LimitOrderCreate(
        user_id=test_users[1]['id'],
        direction=DirectionEnum.SELL,
        ticker=ticker,
        qty=100,
        price=15
    ))

    trade_list1 = test_orderbook.add_order(limit_order)
    market_order = await OrderDAO.add(test_session,  
                                    MarketOrderCreate(
                                        user_id=test_users[0]['id'],
                                        direction=DirectionEnum.BUY,
                                        ticker=ticker,
                                        qty=10,
                                        order_type=OrderEnum.MARKET))
    trade_list = test_orderbook.add_order(market_order)
    
    assert len(trade_list) == 1


@pytest.mark.asyncio
async def test_engine_startup(test_session, filled_test_db, test_instruments, test_orders):
    matching_engine = MatchingEngine(interval= 1.0)
    await matching_engine.startup(session=test_session)
    aapl_bids = await matching_engine.get_bids_from_book(ticker=test_instruments[0]['ticker'])
    aapl_asks = await matching_engine.get_asks_from_book(ticker=test_instruments[0]['ticker'])
    goog_bids = await matching_engine.get_bids_from_book(ticker=test_instruments[1]['ticker'])
    goog_asks = await matching_engine.get_asks_from_book(ticker=test_instruments[1]['ticker'])
    assert len(aapl_bids) == 2
    assert len(aapl_asks) == 0
    assert len(goog_bids) == 0
    assert len(goog_asks) == 1
    assert aapl_bids[0].id == test_orders[0]['id']
    assert goog_asks[0].id == test_orders[2]['id']


@pytest.mark.asyncio
async def test_add_instrument_to_engine(test_session, test_instruments, filled_test_db):
    matching_engine = MatchingEngine(interval=1.0)
    instrument = await InstrumentDAO.find_one_or_none(
        test_session, 
        InstrumentRequest(
            name=test_instruments[0]['name'], 
            ticker=test_instruments[0]['ticker']))
    
    matching_engine.add_instrument(instrument)
    assert len(matching_engine.books) == 1


@pytest.mark.asyncio
async def test_engine_match_all_with_full_verification(
    filled_for_engine_test,
    test_session, 
    test_instruments, 
    test_users
):
    # Запуск
    matching_engine = MatchingEngine(interval=1.0)
    await matching_engine.startup(test_session)
    ticker = test_instruments[0]['ticker']
    buyer_id = test_users[0]['id']
    seller_id = test_users[1]['id']

    # Получаем балансы
    initial_buyer_rub_amount = (await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=buyer_id, ticker="RUB"))).amount # 100
    initial_seller_rub_amount = (await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=seller_id, ticker="RUB"))).amount # 0
    initial_buyer_token_amount = (await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=buyer_id, ticker=ticker))).amount # 10
    initial_seller_token_amount = (await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=seller_id, ticker=ticker))).amount # 30

    # Создаем ордера (покупка за 10, продажа за 5 - должно вернуть 5 сдачи)
    buy_order = await OrderDAO.add(
        test_session,
        LimitOrderCreate(
            user_id=buyer_id,
            direction=DirectionEnum.BUY,
            ticker=ticker,
            qty=10,
            price=10  # вышке чем у продавана
        )
    )
    
    sell_order = await OrderDAO.add(
        test_session,
        LimitOrderCreate(
            user_id=seller_id,
            direction=DirectionEnum.SELL,
            ticker=ticker,
            qty=20,
            price=5  # ниже чем у покупана
        )
    )

    # добавляем ордера запускаем
    await matching_engine.add_order(test_session, buy_order)
    await matching_engine.add_order(test_session, sell_order)
    await matching_engine.match_all(test_session)
    
    # Получаем ордера и проверяем статусы
    updated_buy_order = await OrderDAO.find_one_by_primary_key(test_session, IdRequest(id=buy_order.id))
    updated_sell_order = await OrderDAO.find_one_by_primary_key(test_session, IdRequest(id=sell_order.id))
    
    assert updated_buy_order.status == StatusEnum.EXECUTED
    assert updated_buy_order.filled == 10
    assert updated_sell_order.status == StatusEnum.PARTIALLY_EXECUTED
    assert updated_sell_order.filled == 10  # Ток половина исполнена

    # Получаем транзакции 
    await test_session.flush()
    transactions = await TransactionDAO.find_all(test_session)
    rub_transfers = [t for t in transactions if t.ticker == "RUB"]
    token_transfers = [t for t in transactions if t.ticker == ticker]
    
    # Должен быть 1 перевод руб (buyer -> seller)
    assert len(rub_transfers) == 1 # Error 0 == 1
    assert rub_transfers[0].amount == 50  # 10 * 5 (price)
    assert rub_transfers[0].buyer_id == seller_id  # Продавец получает RUB
    assert rub_transfers[0].seller_id == buyer_id
    
    # Должен быть 1 перевод токенов (seller -> buyer)
    assert len(token_transfers) == 1
    assert token_transfers[0].amount == 10  # 10 tokens
    assert token_transfers[0].buyer_id == buyer_id
    assert token_transfers[0].seller_id == seller_id

    # Проверяем балансы
    # Buyer:
    # - получил RUB: 10 * 5 = 50
    # - получил tokens: 10
    new_buyer_rub = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=buyer_id, ticker="RUB")) # 100
    new_buyer_token = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=buyer_id, ticker=ticker)) # 20
    assert new_buyer_rub.amount == initial_buyer_rub_amount + 50 # Баланс меняется в services, 50 это сдача
    assert new_buyer_token.amount == initial_buyer_token_amount + 10
    
    # Seller:
    # - Получил RUB: 10 * 5 = 50
    # - потратил tokens: 0 (Они тратятся в services, при создании ордера)
    new_seller_rub = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=seller_id, ticker="RUB"))
    new_seller_token = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=seller_id, ticker=ticker))
    assert new_seller_rub.amount == initial_seller_rub_amount + 50
    assert new_seller_token.amount == initial_seller_token_amount # Баланс меняется в services

    assert len(transactions) == 2  