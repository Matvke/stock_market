from sqlalchemy.ext.asyncio import AsyncSession
import pytest
from dao.dao import BalanceDAO, UserDAO, InstrumentDAO, OrderDAO
from services.public import register_user, get_instruments_list, get_transactions_history, get_orderbook
from services.balance import get_balances
from services.order import create_market_order, create_limit_order, get_list_orders, get_order, cancel_order
from services.admin import delete_user, add_instrument, delete_instrument, update_balance
from schemas.request import NewUserRequest, TransactionRequest, MarketOrderRequest, LimitOrderRequest, UserAPIRequest, BalanceRequest, IdRequest, InstrumentRequest, TickerRequest, DepositRequest, WithdrawRequest
from schemas.response import InstrumentResponse, L2OrderBook
from misc.enums import DirectionEnum, StatusEnum, VisibilityEnum
from services.engine import matching_engine
from services.matching import MatchingEngine
from fastapi import HTTPException, status


@pytest.mark.asyncio
async def test_register_user(test_session):
    new_user = await register_user(
        NewUserRequest(name="Pedro"),
        session=test_session  
    )
    assert new_user.name == "Pedro"
    assert new_user.role == "USER"
    assert new_user.api_key.startswith("key-")

    new_user_balances = await get_balances(test_session, new_user.id)
    user = await UserDAO.find_one_or_none(test_session, UserAPIRequest(api_key=new_user.api_key))
    assert user.id == new_user.id
    assert new_user_balances.root == {"RUB": 0}


@pytest.mark.asyncio
async def test_get_instrument_list(test_session: AsyncSession, filled_test_db, test_instruments):
    instrument_list = await get_instruments_list(session=test_session)
    assert isinstance(instrument_list, list) or type(instrument_list) is None
    assert len(instrument_list) == len(test_instruments)
    for i in instrument_list:
        assert isinstance(i, InstrumentResponse)


@pytest.mark.asyncio
async def test_get_orderbook(test_session, filled_test_db, test_orders):
    matching_engine = MatchingEngine()
    matching_engine.startup(test_session)
    l2orderbook: L2OrderBook = await get_orderbook(ticker='AAPL', limit=10)
    assert len(l2orderbook.bid_levels) == 2


@pytest.mark.asyncio
async def test_get_transaction_history(test_session, filled_test_db, test_transactions):
    transactions = await get_transactions_history(test_session, filter_model=TransactionRequest(ticker="AAPL"))
    assert len(transactions) == 1


@pytest.mark.asyncio
async def test_get_balances(test_session, filled_test_db, test_balances, test_users, test_instruments):
    balance_response = await get_balances(test_session, test_users[0]["id"])
    assert len(balance_response.root) == len(test_instruments)
    

@pytest.mark.asyncio
async def test_succesfully_create_market_order(test_session, filled_for_engine_test, test_users, test_instruments, test_balances):
    buyer_user_id = test_users[0]['id']
    seller_user_id = test_users[1]['id']
    ticker = test_instruments[0]['ticker']
    await create_limit_order(
        test_session,
        user_id=buyer_user_id,
        order_data=LimitOrderRequest(
            direction=DirectionEnum.BUY,
            ticker=ticker,
            qty=3,
            price=10
        )
    )
    await create_market_order(
        test_session,
        user_id=seller_user_id,
        order_data=MarketOrderRequest(
            direction=DirectionEnum.SELL,
            ticker=ticker,
            qty=2
        )
    )
    buyer_balance = await BalanceDAO.find_one_by_primary_key(test_session, BalanceRequest(user_id=buyer_user_id, ticker=ticker))
    seller_balance = await BalanceDAO.find_one_by_primary_key(test_session, BalanceRequest(user_id=seller_user_id, ticker="RUB"))

    assert buyer_balance.amount == test_balances[0]['amount'] + 2
    assert seller_balance.amount == test_balances[4]['amount'] + 20


@pytest.mark.asyncio
async def test_unsuccesfully_create_market_order_with_no_money(test_session, filled_test_db, test_users, test_instruments):
    try:
        await create_market_order(
            test_session, 
            test_users[0]["id"], 
            MarketOrderRequest(
                direction=DirectionEnum.BUY,
                ticker=test_instruments[0]["ticker"],
                qty=2000))
    except Exception as e:
        assert e.status_code == 400


@pytest.mark.asyncio
async def test_succesfully_create_limit_order(test_session, filled_test_db, test_users, test_instruments, test_balances):
    limit_order_output = await create_limit_order(
        test_session,
        test_users[0]["id"],
        LimitOrderRequest(
            direction=DirectionEnum.BUY,
            ticker=test_instruments[0]["ticker"],
            qty=2,
            price=10
        )
    )
    user_balance_after = await BalanceDAO.find_one_by_primary_key(test_session, BalanceRequest(user_id=test_users[0]["id"], ticker='RUB'))
    assert user_balance_after.amount == test_balances[2]['amount'] - 20
    assert limit_order_output.success


@pytest.mark.asyncio
async def test_create_limit_order_with_no_rub(test_session, filled_test_db, test_users, test_instruments):
    try:
        await create_limit_order(
            test_session,
            test_users[1]["id"],
            LimitOrderRequest(
                direction=DirectionEnum.BUY,
                ticker=test_instruments[0]["ticker"],
                qty=1,
                price=100
            )
        )
    except Exception as e:
        assert e.status_code == 400


@pytest.mark.asyncio
async def test_get_list_orders(test_session, filled_test_db, test_users, test_instruments):
    list_orders = await get_list_orders(test_session, test_users[0]["id"])
    assert len(list_orders) == 2


@pytest.mark.asyncio
async def test_get_order(test_session, filled_test_db, test_users, test_instruments, test_orders):
    order = await get_order(test_session, test_users[1]["id"], test_orders[1]["id"])
    assert order.body.ticker == test_orders[1]["ticker"]


@pytest.mark.asyncio
async def test_cancel_sell_order(test_session, default_init_db):
    user1 = await register_user(NewUserRequest(name="Tester"), test_session)
    await add_instrument(test_session, InstrumentRequest(name="MEMECOIN", ticker="MEMECOIN"))
    await update_balance(test_session, DepositRequest(user_id=user1.id, ticker='MEMECOIN', amount=3))
    lo1 = await create_limit_order(test_session, user1.id, LimitOrderRequest(direction=DirectionEnum.SELL, ticker="MEMECOIN", qty=3, price=10))
    await cancel_order(test_session, user1.id, lo1.order_id)
    await test_session.commit()

    order1 = await OrderDAO.find_one_or_none(test_session, IdRequest(id=lo1.order_id))
    balance1 = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=user1.id, ticker="MEMECOIN"))
    assert order1.status == StatusEnum.CANCELLED
    assert balance1.amount == 3


@pytest.mark.asyncio
async def test_cancel_buy_order(test_session, default_init_db):
    user2 = await register_user(NewUserRequest(name="Tester"), test_session)
    await add_instrument(test_session, InstrumentRequest(name="MEMECOIN", ticker="MEMECOIN"))
    await update_balance(test_session, DepositRequest(user_id=user2.id, ticker='RUB', amount=100))
    lo2 = await create_limit_order(test_session, user2.id, LimitOrderRequest(direction=DirectionEnum.BUY, ticker="MEMECOIN", qty=3, price=10))
    await cancel_order(test_session, user2.id, lo2.order_id)
    await test_session.commit()

    order2 = await OrderDAO.find_one_or_none(test_session, IdRequest(id=lo2.order_id))
    balance2 = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=user2.id, ticker="RUB"))
    assert order2.status == StatusEnum.CANCELLED
    assert balance2.amount == 100





@pytest.mark.asyncio
async def test_delete_user(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    output = await delete_user(test_session, test_users[0]['id'])
    assert output.id == test_users[0]['id']
    user = await UserDAO.find_one_by_primary_key(test_session, IdRequest(id=test_users[0]['id']))
    assert not user

@pytest.mark.asyncio
async def test_add_instrument(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    output = await add_instrument(test_session, InstrumentRequest(name="test", ticker="TST"))
    assert matching_engine.books.get("TST")
    assert output.success 
    instrument = await InstrumentDAO.find_one_by_primary_key(test_session, TickerRequest(ticker="TST"))
    assert instrument.visibility == VisibilityEnum.ACTIVE
    assert instrument.name == "test"
    assert instrument.ticker == "TST"


@pytest.mark.asyncio
async def test_delete_instrument(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    output = await delete_instrument(test_session, ticker=test_instruments[1]['ticker'])
    assert output.success 
    instrument = await InstrumentDAO.find_one_by_primary_key(test_session, TickerRequest(ticker=test_instruments[1]["ticker"]))
    assert not instrument


@pytest.mark.asyncio
async def test_deposit(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    output = await update_balance(
        test_session, 
        DepositRequest(
            user_id=test_users[0]['id'],
            ticker=test_instruments[0]['ticker'],
            amount=20))
    
    assert output.success 
    balance = await BalanceDAO.find_one_by_primary_key(
        test_session, 
        BalanceRequest(user_id=test_users[0]['id'],
                       ticker=test_instruments[0]['ticker']))
    
    assert balance.amount == test_balances[0]['amount'] + 20


@pytest.mark.asyncio
async def test_withdraw(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    output = await update_balance(
        test_session, 
        WithdrawRequest(
            user_id=test_users[0]['id'],
            ticker=test_instruments[0]['ticker'],
            amount=10))
    
    assert output.success 
    balance = await BalanceDAO.find_one_by_primary_key(
        test_session, 
        BalanceRequest(user_id=test_users[0]['id'],
                       ticker=test_instruments[0]['ticker']))
    
    assert balance.amount == test_balances[0]['amount'] - 10


@pytest.mark.asyncio
async def test_add_and_delete_instrument(
    filled_for_engine_test,
    test_session, 
    test_instruments, 
    test_users
):
    instrument = InstrumentRequest(name="MEMECOIN", ticker="MEME")
    await add_instrument(test_session, instrument)
    assert matching_engine.books.get(instrument.ticker)
    await delete_instrument(test_session, ticker=instrument.ticker)
    assert not matching_engine.books.get(instrument.ticker)
    await add_instrument(test_session, instrument)
    instrument_in_db = await InstrumentDAO.find_one_or_none(test_session, instrument)
    assert instrument_in_db.visibility == VisibilityEnum.ACTIVE
    assert instrument.ticker == instrument_in_db.ticker
    assert matching_engine.books.get(instrument.ticker)

# INFO (21-05-2025 11:46:20):      Added new order (UUID('c3b0da53-bb91-409b-9c87-9352d814ff9d'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 100, 1, <OrderEnum.LIMIT: 'LIMIT'>)
# INFO (21-05-2025 11:46:20):      Added new order (UUID('9290ba2b-bba4-4ad4-ae31-4ac8cc773225'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 150, 2, <OrderEnum.LIMIT: 'LIMIT'>)
# INFO (21-05-2025 11:46:20):      Updated user a545addb-ab74-440c-84f9-26ca7b8eb7e5 balance RUB to 1000 by admin.
# INFO (21-05-2025 11:46:20):      Added new order (UUID('0af821af-745c-4c34-a24c-7ca3526dc940'), 'MEMECOIN', <DirectionEnum.BUY: 'BUY'>, None, 2, <OrderEnum.MARKET: 'MARKET'>)

@pytest.mark.asyncio
async def test_basic(test_session, default_init_db):
    user1 = await register_user(NewUserRequest(name="Pedro"), test_session) 
    user2 = await register_user(NewUserRequest(name="Antonio"), test_session) 

    await add_instrument(test_session, InstrumentRequest(name="MEMECOIN", ticker="MEMECOIN"))
    
    await update_balance(test_session, DepositRequest(user_id=user1.id, ticker="MEMECOIN", amount=3))
    await update_balance(test_session, DepositRequest(user_id=user2.id, ticker="RUB", amount=1000))

    lo1 =await create_limit_order(test_session, user1.id, LimitOrderRequest(direction=DirectionEnum.SELL, ticker="MEMECOIN", qty=1, price=100))
    await create_limit_order(test_session, user1.id, LimitOrderRequest(direction=DirectionEnum.SELL, ticker="MEMECOIN", qty=2, price=150))
    await create_market_order(test_session, user2.id, MarketOrderRequest(direction=DirectionEnum.BUY, ticker="MEMECOIN", qty=2))

    list_orders = await get_list_orders(test_session, user1.id)
    assert len(list_orders) == 2 
    await test_session.commit()

    try:
        await cancel_order(test_session, user1.id, order_id=lo1.order_id)
    except HTTPException as e:
        assert e.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_get_market_order(test_session, default_init_db):
    user1 = await register_user(NewUserRequest(name="Pedro"), test_session) 
    user2 = await register_user(NewUserRequest(name="Antonio"), test_session) 
    await add_instrument(test_session, InstrumentRequest(name="MEMECOIN", ticker="MEMECOIN"))

    await update_balance(test_session, DepositRequest(user_id=user1.id, ticker="MEMECOIN", amount=3))
    await update_balance(test_session, DepositRequest(user_id=user2.id, ticker="RUB", amount=200))

    await create_limit_order(test_session, user1.id, LimitOrderRequest(direction=DirectionEnum.SELL, ticker="MEMECOIN", qty=3, price=100))
    await create_market_order(test_session, user2.id, MarketOrderRequest(direction=DirectionEnum.BUY, ticker="MEMECOIN", qty=2))
    
    orders_list = await get_list_orders(test_session, user2.id)
    assert len(orders_list) == 1

    await test_session.commit()
    balance2 = await BalanceDAO.find_one_or_none(test_session, BalanceRequest(user_id=user2.id, ticker="RUB"))
    assert balance2.amount == 0 # Error 200 != 0
    

