from datetime import datetime
from uuid import uuid4
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from dao.database import Base
from sqlalchemy import insert, text
from misc.db_models import Instrument, Order, User, Transaction, Balance
from misc.enums import DirectionEnum
from main import app
from fastapi.testclient import TestClient
from dependencies import get_db, token
from services.engine import matching_engine


@pytest_asyncio.fixture
async def client(test_session):
    app.dependency_overrides[get_db] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(test_session, test_users):
    app.dependency_overrides[get_db] = lambda: test_session
    yield TestClient(app=app, headers={
        "Authorization": f"{token} {test_users[0]["api_key"]}"
    })
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(test_session, test_users):
    app.dependency_overrides[get_db] = lambda: test_session
    yield TestClient(app=app, headers={
        "Authorization": f"{token} {test_users[3]["api_key"]}"
    })
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
    async with async_sessionmaker(
        test_db_engine, expire_on_commit=False
    )() as session:
        yield session


@pytest_asyncio.fixture
async def test_users():
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
            "role": "USER",
            "api_key": f"key-{uuid4()}"
        },
        {
            "id": uuid4(),
            "name": "Сергей Сидоров",
            "role": "USER",
            "api_key": f"key-{uuid4()}"
        },
        {
            "id": uuid4(),
            "name": "Админ Админов",
            "role": "ADMIN",
            "api_key": f"key-{uuid4()}"
        }
    ]

@pytest_asyncio.fixture
async def test_instruments():
    return [
        {"ticker": "AAPL", "name": "Apple Inc"},
        {"ticker": "GOOG", "name": "Alphabet Inc"},
        {"ticker": "RUB", "name": "Russian Ruble"}
    ]

@pytest_asyncio.fixture
async def test_orders(test_users, test_instruments):
    return [
        {
            "id": uuid4(),
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[0]["ticker"],
            "direction": DirectionEnum.BUY,
            "qty": 100,
            "price": 15,
            "status": "NEW",
            "filled": 0,
            "order_type": "LIMIT",
            "created_at": datetime.now()
        },
        {
            "id": uuid4(),
            "user_id": test_users[1]["id"],
            "ticker": test_instruments[0]["ticker"],
            "direction": DirectionEnum.BUY,
            "qty": 50,
            "price": 10,
            "status": "NEW",
            "filled": 0,
            "order_type": "LIMIT",
            "created_at": datetime.now()
        },
        {
            "id": uuid4(),
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[1]["ticker"],
            "direction": DirectionEnum.SELL,
            "qty": 21,
            "price": 10,
            "status": "NEW",
            "filled": 0,
            "order_type": "LIMIT",
            "created_at": datetime.now()
        }
    ]


@pytest_asyncio.fixture
async def test_transactions(test_users, test_instruments):
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


@pytest_asyncio.fixture
async def test_balances(test_users, test_instruments):
    return [
        {
            "user_id": test_users[0]["id"],
            "ticker": test_instruments[0]["ticker"],
            "amount": 10
        },
        {
            "user_id": test_users[0]["id"], # Seller
            "ticker": test_instruments[1]["ticker"], # goog
            "amount": 20
        },
        {
            "user_id": test_users[0]["id"], 
            "ticker": test_instruments[2]["ticker"],
            "amount": 100
        },
        {
            "user_id": test_users[1]["id"],
            "ticker": test_instruments[0]["ticker"], 
            "amount": 30
        },
        { 
            "user_id": test_users[1]["id"], # buyer
            "ticker": test_instruments[2]["ticker"], # rub
            "amount": 100
        },
        {
            "user_id": test_users[2]["id"],
            "ticker": test_instruments[2]["ticker"],
            "amount": 0
        }
    ]



@pytest_asyncio.fixture
async def filled_test_db(test_session, test_users, test_instruments, test_orders, test_transactions, test_balances):
    async with test_session.begin():
        await test_session.execute(text("DELETE FROM transactions;"))
        await test_session.execute(text("DELETE FROM orders;"))
        await test_session.execute(text("DELETE FROM instruments;")) 
        await test_session.execute(text("DELETE FROM users;"))
        await test_session.execute(text("DELETE FROM balances"))

        await test_session.execute(text("INSERT INTO instruments VALUES('PPK', 'POPKA', 'DELETED')"))
        await test_session.execute(insert(User), test_users)
        await test_session.execute(insert(Instrument), test_instruments)
        await test_session.execute(insert(Order), test_orders)
        await test_session.execute(insert(Transaction), test_transactions)
        await test_session.execute(insert(Balance), test_balances)

        await matching_engine_startup(test_session)


@pytest_asyncio.fixture
async def filled_for_engine_test(test_session: AsyncSession, test_users, test_instruments, test_balances):
    async with test_session.begin():
        await test_session.execute(text("DELETE FROM balances;"))
        await test_session.execute(text("DELETE FROM instruments;"))
        await test_session.execute(text("DELETE FROM users;"))

        await test_session.execute(insert(User), test_users)
        await test_session.execute(insert(Instrument), test_instruments)
        await test_session.execute(insert(Balance), test_balances)
        
        await matching_engine_startup(test_session)


async def matching_engine_startup(test_session):
    await matching_engine.startup(test_session)
