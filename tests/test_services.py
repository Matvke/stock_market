from sqlalchemy.ext.asyncio import AsyncSession
import pytest
from dao.dao import BalanceDAO, UserDAO, InstrumentDAO
from services.public import register_user, get_instruments_list, get_transactions_history, get_orderbook
from services.balance import get_balances
from services.order import create_market_order, create_limit_order, get_list_orders, get_order, cancel_order
from services.admin import delete_user, add_instrument, delete_instrument, update_balance
from schemas.request import NewUserRequest, TransactionRequest, MarketOrderRequest, LimitOrderRequest, UserAPIRequest, BalanceRequest, IdRequest, InstrumentRequest, TickerRequest, DepositRequest, WithdrawRequest
from schemas.response import InstrumentResponse, L2OrderBook
from misc.enums import DirectionEnum, StatusEnum, VisibilityEnum
from services.engine import matching_engine
from services.matching import MatchingEngine


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
async def test_cancel_buy_order(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    order_cancel_output = await cancel_order(test_session, test_users[0]["id"], test_orders[0]["id"]) 
    order_after = await get_order(test_session, test_users[0]["id"], test_orders[0]["id"])
    balance_after = await BalanceDAO.find_one_by_primary_key(test_session, 
                                                             BalanceRequest(
                                                                 user_id=test_users[0]["id"], 
                                                                 ticker="RUB"))
    assert balance_after.amount == test_balances[2]['amount'] + (test_orders[0]['qty'] - test_orders[0]['filled']) * test_orders[0]['price']
    assert order_cancel_output.success
    assert order_after.status == StatusEnum.CANCELLED


@pytest.mark.asyncio
async def test_cancel_sell_order(test_session, filled_test_db, test_users, test_instruments, test_orders, test_balances):
    order_cancel_output = await cancel_order(test_session, test_users[0]["id"], test_orders[2]["id"]) 
    order_after = await get_order(test_session, test_users[0]["id"], test_orders[2]["id"])
    balance_after = await BalanceDAO.find_one_by_primary_key(test_session, 
                                                             BalanceRequest(
                                                                 user_id=test_users[0]["id"], 
                                                                 ticker=test_orders[2]['ticker']))
    assert balance_after.amount == test_balances[1]['amount'] + test_orders[2]['qty'] - test_orders[2]['filled']
    assert order_cancel_output.success 
    assert order_after.status == StatusEnum.CANCELLED


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