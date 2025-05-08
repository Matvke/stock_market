from pydantic import ValidationError
import pytest
from fastapi import status
from schemas.response import L2OrderBook, InstrumentResponse, UserResponse, TransactionResponse


@pytest.mark.asyncio
async def test_register_user(auth_client, filled_test_db):
    response = auth_client.post("/api/v1/public/register", json={"name": "Pedro"})
    assert response.status_code == 200
    assert response.json()["name"] == "Pedro"
    try:
        UserResponse.model_validate(response.json())
    except ValidationError as e:
        pytest.fail(f"Response doesn't match schema: {e}")


@pytest.mark.asyncio
async def test_get_instruments(auth_client, filled_test_db, test_instruments):
    response = auth_client.get("/api/v1/public/instrument")
    assert response.status_code == 200
    for item in response.json():
        try:
            InstrumentResponse.model_validate(item)
        except ValidationError as e:
            pytest.fail(f"Item {item} doesn't match schema: {e}")
    assert len(response.json()) == len(test_instruments)


@pytest.mark.asyncio
async def test_get_orderbook(auth_client, filled_test_db):
    response = auth_client.get("/api/v1/public/orderbook/AAPL")
    assert response.status_code == 200
    try:
        L2OrderBook.model_validate(response.json())
    except ValidationError as e:
        pytest.fail(f"Response doesn't match schema: {e}")
    assert len(L2OrderBook.model_validate(response.json()).bid_levels) == 2


@pytest.mark.asyncio
async def test_get_transactions_history(auth_client, filled_test_db):
    response = auth_client.get("/api/v1/public/transactions/AAPL")
    assert response.status_code == 200
    for item in response.json():
        try:
            TransactionResponse.model_validate(item)
        except ValidationError as e:
            pytest.fail(f"Item {item} doesn't match schema: {e}")
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_get_balances_unauthorized(client, filled_test_db):
    response = client.get("/api/v1/balance")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_balances_authorized(auth_client, filled_test_db, test_users):
    response = auth_client.get(
        "/api/v1/balance",
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), dict)
    print(response.json())
    assert response.json() == {'AAPL': 10, 'GOOG': 20, 'RUB': 100}


@pytest.mark.asyncio
async def test_create_market_order(auth_client, filled_test_db, test_instruments, test_orders):
    response = auth_client.post(
        "/api/v1/order",
        json={
            "direction": "SELL",
            "ticker": test_instruments[0]["ticker"],
            "qty": 2
        },
        headers={"Content-Type": "application/json"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_create_limit_order(auth_client, filled_test_db, test_instruments):
    response = auth_client.post(
        "/api/v1/order",
        json={
            "direction" : "BUY",
            "ticker": test_instruments[0]["ticker"],
            "qty": 2,
            "price": 10
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_get_list_orders(auth_client, filled_test_db, test_instruments, test_orders):
    response = auth_client.get(
        "/api/v1/order"
    )
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_get_order(auth_client, filled_test_db, test_instruments, test_orders):
    response = auth_client.get(
        f"/api/v1/order/{test_orders[0]['id']}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()['body']['ticker'] == test_orders[1]["ticker"]


@pytest.mark.asyncio
async def test_cancel_order(auth_client, filled_test_db, test_instruments, test_orders):
    response = auth_client.delete(
        f"/api/v1/order/{test_orders[0]["id"]}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_delete_user(admin_client, filled_test_db, test_instruments, test_orders, test_users):
    response = admin_client.delete(
        f"/api/v1/admin/user/{test_users[0]['id']}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == str(test_users[0]['id'])


@pytest.mark.asyncio
async def test_create_instrument(admin_client, filled_test_db, test_instruments, test_orders, test_users):
    response = admin_client.post(
        "/api/v1/admin/instrument",
        json={
            "name" : "ROCKET",
            "ticker": "RKT",
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_delete_instrument(admin_client, filled_test_db, test_instruments, test_orders, test_users):
    response = admin_client.delete(
        f"/api/v1/admin/instrument/{test_instruments[1]["ticker"]}"
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_deposit(admin_client, filled_test_db, test_instruments, test_orders, test_users):
    response = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : str(test_users[0]["id"]),
            "ticker": test_instruments[1]["ticker"],
            "amount": 3
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]


@pytest.mark.asyncio
async def test_withdraw(admin_client, filled_test_db, test_instruments, test_orders, test_users):
    response = admin_client.post(
        "/api/v1/admin/balance/withdraw",
        json={
            "user_id" : str(test_users[0]["id"]),
            "ticker": test_instruments[1]["ticker"],
            "amount": 3
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["success"]