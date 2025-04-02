from datetime import datetime
from uuid import uuid4
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dao.database import Base
from sqlalchemy import insert, text, select
from misc.db_models import Instrument, Order, User, Transaction, Balance
from misc.enums import DirectionEnun
from main import app
from fastapi.testclient import TestClient
from dependencies import get_current_user, get_db


@pytest_asyncio.fixture
async def test_user(test_session):
    user = User(
        id=uuid4(),
        name="test_user",
        api_key="key-test",
        role="USER"
    )
    instrument = Instrument(
        ticker="AAPL",
        name="Apple Inc"
    )
    balance = Balance(
        user_id = user.id,
        ticker = instrument.ticker,
        amount = 10
    )
    test_session.add(user)
    test_session.add(instrument)
    test_session.add(balance)

    await test_session.commit()
    return user


@pytest_asyncio.fixture
async def auth_client(test_session, test_user):
    app.dependency_overrides.clear()
    
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides.update({
        get_db: lambda: test_session,
        get_current_user: override_get_current_user
    })
    
    client = TestClient(app)
    client.headers.update({
        "Authorization": f"Bearer {test_user.api_key}"
    })
    yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_session, test_user):
    app.dependency_overrides[get_db] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_db_engine):
    async with sessionmaker(
        test_db_engine, expire_on_commit=False, class_=AsyncSession
    )() as session:
        yield session


@pytest.fixture
def test_users():
    return [
        {
            "id": uuid4(),
            "name": "Иван Петров",
            "role": "USER",
            "api_key": f"key-{uuid4()}"
        },
        {
            "id": uuid4(),
            "name": "Марья Иванова", 
            "role": "ADMIN",
            "api_key": f"key-{uuid4()}"
        },
        {
            "id": uuid4(),
            "name": "Сергей Сидоров",
            "role": "USER",
            "api_key": f"key-{uuid4()}"
        }
    ]

@pytest.fixture 
def test_instruments():
    return [
        {"ticker": "AAPL", "name": "Apple Inc"},
        {"ticker": "GOOG", "name": "Alphabet Inc"}
    ]

@pytest.fixture
def test_orders(test_users, test_instruments):
    return [
        {
            "id": uuid4(),
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[0]["ticker"],
            "direction": DirectionEnun.BUY,
            "qty": 100,
            "price": 15000,
            "status": "NEW",
            "filled": 0,
            "order_type": "LIMIT",
            "created_at": datetime.now()
        },
        {
            "id": uuid4(),
            "user_id": test_users[1]["id"],
            "ticker": test_instruments[0]["ticker"],
            "direction": DirectionEnun.BUY,
            "qty": 50,
            "price": 10000,
            "status": "NEW",
            "filled": 0,
            "order_type": "LIMIT",
            "created_at": datetime.now()
        }
    ]


@pytest.fixture
def test_transactions(test_users, test_instruments):
    return [
        {
            "id": uuid4(),
            "buyer_id": test_users[0]["id"], 
            "seller_id": test_users[1]["id"], 
            "ticker": test_instruments[0]["ticker"], 
            "amount": 100,
            "price": 15000,   
            "timestamp": datetime.now()
        },
        {
            "id": uuid4(),
            "buyer_id": test_users[2]["id"],  
            "seller_id": test_users[0]["id"], 
            "ticker": test_instruments[1]["ticker"], 
            "amount": 50,
            "price": 25000,   
            "timestamp": datetime.now()
        }
    ]


@pytest.fixture
def test_balances(test_users, test_instruments):
    return [
        {
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[0]["ticker"],
            "amount": 10
        },
        {
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[1]["ticker"],
            "amount": 20
        },
        {
            "user_id": test_users[1]["id"],
            "ticker": test_instruments[1]["ticker"],
            "amount": 30
        },
    ]



@pytest_asyncio.fixture
async def filled_test_db(test_session, test_users, test_instruments, test_orders, test_transactions, test_balances):
    # await test_session.execute(text("DELETE FROM orders;"))
    # await test_session.execute(text("DELETE FROM instruments;")) 
    # await test_session.execute(text("DELETE FROM users;"))
    
    await test_session.execute(insert(User), test_users)
    await test_session.execute(insert(Instrument), test_instruments)
    await test_session.execute(insert(Order), test_orders)
    await test_session.execute(insert(Transaction), test_transactions)
    await test_session.execute(insert(Balance), test_balances)
    
    await test_session.commit()
    
    return test_session