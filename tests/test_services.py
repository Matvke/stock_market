import pytest
from services.public import register_user, get_instruments_list, get_orderbook, get_transactions_history
from schemas.request import NewUserRequest, OrderbookRequest, TransactionRequest
from schemas.response import InstrumentResponse, Level
from misc.enums import DirectionEnun
from typing import List


@pytest.mark.asyncio
async def test_register_user(test_session):
    new_user = await register_user(
        NewUserRequest(name="Pedro"),
        session=test_session  
    )
    assert new_user.name == "Pedro"
    assert new_user.role == "USER"
    assert new_user.api_key.startswith("key-")


@pytest.mark.asyncio
async def test_get_instrument_list(test_session, filled_test_db, test_instruments):
    instrument_list = await get_instruments_list(session=test_session)
    assert type(instrument_list) == list or type(instrument_list) == None
    assert len(instrument_list) == len(test_instruments)
    for i in instrument_list:
        assert isinstance(i, InstrumentResponse)


@pytest.mark.asyncio
async def test_get_bid_level(test_session, filled_test_db, test_orders):
    orderbook = await get_orderbook(session=test_session, filter_model=OrderbookRequest(ticker="AAPL", direction=DirectionEnun.BUY))
    assert isinstance(orderbook, list)
    assert len(orderbook) == len(test_orders)
    for o in orderbook:
        assert isinstance(o, Level)

    
@pytest.mark.asyncio
async def test_get_transaction_history(test_session, filled_test_db, test_transactions):
    transactions = await get_transactions_history(test_session, filter_model=TransactionRequest(ticker="AAPL"))
    assert len(transactions) == 1


