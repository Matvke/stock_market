from httpx import Client
from pydantic import ValidationError
import pytest
from fastapi import Response, status
from schemas.response import L2OrderBook, InstrumentResponse, UserResponse, TransactionResponse
from dependencies import token

@pytest.mark.asyncio
async def test_register_user(client, auth_client, filled_test_db):
    response = client.post("/api/v1/public/register", json={"name": "Pedro"})
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


@pytest.mark.asyncio
async def test_bad_cases(client):
    response = client.delete(
        "/order/dont_exist"
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_limit_order_matching(auth_client, filled_test_db, test_instruments):
    # Покупка ниже лучшей цены — не должна исполняться
    auth_client.post("/api/v1/order", json={"direction": "SELL", "ticker": "AAPL", "qty": 2, "price": 100})
    response = auth_client.post("/api/v1/order", json={"direction": "BUY", "ticker": "AAPL", "qty": 2, "price": 50})
    assert response.status_code == 200
    assert response.json()["success"]
    
    # Проверка, что ордер остался в стакане
    orderbook = auth_client.get("/api/v1/public/orderbook/AAPL").json()
    assert any(level["price"] == 50 for level in orderbook["bid_levels"])


@pytest.mark.asyncio
async def test_order_with_zero_qty(auth_client, filled_test_db):
    response = auth_client.post("/api/v1/order", json={"direction": "BUY", "ticker": "AAPL", "qty": 0, "price": 10})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_order_with_negative_price(auth_client, filled_test_db):
    response = auth_client.post("/api/v1/order", json={"direction": "SELL", "ticker": "AAPL", "qty": 1, "price": -5})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_admin_cannot_deposit_negative(admin_client, filled_test_db, test_users, test_instruments):
    response = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : str(test_users[0]["id"]),
            "ticker": test_instruments[1]["ticker"],
            "amount": -53
        },
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422

# INFO (21-05-2025 11:46:20):      Added new order (UUID('c3b0da53-bb91-409b-9c87-9352d814ff9d'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 100, 1, <OrderEnum.LIMIT: 'LIMIT'>)
# INFO (21-05-2025 11:46:20):      Added new order (UUID('9290ba2b-bba4-4ad4-ae31-4ac8cc773225'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 150, 2, <OrderEnum.LIMIT: 'LIMIT'>)
# INFO (21-05-2025 11:46:20):      Updated user a545addb-ab74-440c-84f9-26ca7b8eb7e5 balance RUB to 1000 by admin.
# INFO (21-05-2025 11:46:20):      Added new order (UUID('0af821af-745c-4c34-a24c-7ca3526dc940'), 'MEMECOIN', <DirectionEnum.BUY: 'BUY'>, None, 2, <OrderEnum.MARKET: 'MARKET'>)
# ERROR (21-05-2025 11:46:20):      Ошибка в маркет ордере, еблан тупой.
# INFO (21-05-2025 11:46:20):      Запрошен лист ордеров для a9e42dd9-0038-45b0-8f2b-9b3ba3a84eea: 2
# INFO (21-05-2025 11:46:20):      Trying cancel order (UUID('c3b0da53-bb91-409b-9c87-9352d814ff9d'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 100, 1, <OrderEnum.LIMIT: 'LIMIT'>)
# INFO (21-05-2025 11:46:20):      Order cancel error: order (UUID('c3b0da53-bb91-409b-9c87-9352d814ff9d'), 'MEMECOIN', <DirectionEnum.SELL: 'SELL'>, 100, 1, <OrderEnum.LIMIT: 'LIMIT'>) not found.
# ERROR (21-05-2025 11:46:20):      Рассинхрон БД и движка.
# TODO Тест возврата сдачи


@pytest.mark.asyncio
async def test_basic(admin_client, client, default_init_db):
    user1 = client.post("/api/v1/public/register", json={"name": "Pedro"})
    user1 = user1.json()
    user2 = client.post("/api/v1/public/register", json={"name": "Antonio"})
    user2 = user2.json()

    instrument = admin_client.post(
        "/api/v1/admin/instrument",
        json={
            "name" : "MEMECOIN",
            "ticker": "MEMECOIN",
        },
        headers={"Content-Type": "application/json"}
    )
    assert instrument.status_code == status.HTTP_200_OK

    deposit_tickers_to_user1 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user1["id"],
            "ticker": "MEMECOIN",
            "amount": 3
        },
        headers={"Content-Type": "application/json"}
    )

    assert deposit_tickers_to_user1.status_code == status.HTTP_200_OK


    deposit_rub_to_user2 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user2["id"],
            "ticker": "RUB",
            "amount": 1000
        },
        headers={"Content-Type": "application/json"}
    )

    assert deposit_rub_to_user2.status_code == status.HTTP_200_OK

    create_limit_order1 = client.post(
        "/api/v1/order", 
        json={
            "direction": "SELL", 
            "ticker": "MEMECOIN", 
            "qty": 1, 
            "price": 100},

        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )

    assert create_limit_order1.status_code == status.HTTP_200_OK

    create_limit_order2 = client.post(
        "/api/v1/order", 
        json={
            "direction": "SELL", 
            "ticker": "MEMECOIN", 
            "qty": 2, 
            "price": 150},

        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    
    assert create_limit_order2.status_code == status.HTTP_200_OK

    create_market_order2 = client.post(
        "/api/v1/order", 
        json={
            "direction": "BUY", 
            "ticker": "MEMECOIN", 
            "qty": 2},

        headers={
            "Authorization": f"{token} {user2["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert create_market_order2.status_code == status.HTTP_200_OK

    list_orders = client.get(
        "/api/v1/order",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert len(list_orders.json()) == 2

    cancel_order = client.delete(
        f"/api/v1/order/{create_limit_order1.json()['order_id']}",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert cancel_order.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_cancel_orders(admin_client, client: Client, default_init_db):
    user1: Response = client.post("/api/v1/public/register", json={"name": "Pedro"})
    user1 = user1.json()
    
    instrument = admin_client.post(
        "/api/v1/admin/instrument",
        json={
            "name" : "MEMECOIN",
            "ticker": "MEMECOIN",
        },
        headers={"Content-Type": "application/json"}
    )
    assert instrument.status_code == status.HTTP_200_OK

    deposit_tickers_to_user1 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user1["id"],
            "ticker": "MEMECOIN",
            "amount": 3
        },
        headers={"Content-Type": "application/json"}
    )
    assert deposit_tickers_to_user1.status_code == status.HTTP_200_OK

    deposit_rub_to_user1 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user1["id"],
            "ticker": "RUB",
            "amount": 100
        },
        headers={"Content-Type": "application/json"}
    )
    assert deposit_rub_to_user1.status_code == status.HTTP_200_OK

    create_limit_order1 = client.post(
        "/api/v1/order", 
        json={
            "direction": "SELL", 
            "ticker": "MEMECOIN", 
            "qty": 3, 
            "price": 150},

        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    
    assert create_limit_order1.status_code == status.HTTP_200_OK

    balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    balance = balance.json()
    assert balance["MEMECOIN"] == 0
    assert balance["RUB"] == 100

    cancel_order1 = client.delete(
        f"/api/v1/order/{create_limit_order1.json()['order_id']}",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert cancel_order1.status_code == status.HTTP_200_OK

    balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    balance = balance.json()
    assert balance["MEMECOIN"] == 3
    assert balance["RUB"] == 100

    create_limit_order2 = client.post(
        "/api/v1/order", 
        json={
            "direction": "BUY", 
            "ticker": "MEMECOIN", 
            "qty": 1,
            "price": 100},

        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert create_limit_order2.status_code == status.HTTP_200_OK

    balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    balance = balance.json()
    assert balance["MEMECOIN"] == 3
    assert balance["RUB"] == 0

    cancel_order2 = client.delete(
        f"/api/v1/order/{create_limit_order2.json()['order_id']}",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert cancel_order2.status_code == status.HTTP_200_OK

    balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    balance = balance.json()
    assert balance["MEMECOIN"] == 3
    assert balance["RUB"] == 100

# [22.05.2025, 14:47:59] [main-container-090dr-built] INFO: 127.0.0.1:34958 - "GET /api/v1/order HTTP/1.1" 500 Internal Server Error
# [22.05.2025, 14:47:59] [main-container-090dr-built] INFO (22-05-2025 09:47:59): Запрошен лист ордеров для 62ada99d-d4f1-495e-beb3-b484b5a2bfb1: 1
# [22.05.2025, 14:47:59] [main-container-090dr-built] INFO: 127.0.0.1:34958 - "POST /api/v1/order HTTP/1.1" 200 OK

@pytest.mark.asyncio
async def test_get_created_order(admin_client: Client, client: Client, default_init_db):
    user1 = client.post("/api/v1/public/register", json={"name": "Pedro"})
    user1 = user1.json()
    user2 = client.post("/api/v1/public/register", json={"name": "Pedro"})
    user2 = user2.json()

    instrument = admin_client.post(
        "/api/v1/admin/instrument",
        json={
            "name" : "MEMECOIN",
            "ticker": "MEMECOIN",
        },
        headers={"Content-Type": "application/json"}
    )
    assert instrument.status_code == status.HTTP_200_OK

    deposit_tickers_to_user1 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user1["id"],
            "ticker": "MEMECOIN",
            "amount": 3
        },
        headers={"Content-Type": "application/json"}
    )
    assert deposit_tickers_to_user1.status_code == status.HTTP_200_OK

    deposit_rub_to_user2 = admin_client.post(
        "/api/v1/admin/balance/deposit",
        json={
            "user_id" : user2["id"],
            "ticker": "RUB",
            "amount": 200
        },
        headers={"Content-Type": "application/json"}
    )
    assert deposit_rub_to_user2.status_code == status.HTTP_200_OK

    create_limit_order2 = client.post(
        "/api/v1/order", 
        json={
            "direction": "SELL", 
            "ticker": "MEMECOIN", 
            "qty": 3,
            "price": 100},

        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert create_limit_order2.status_code == status.HTTP_200_OK

    create_market_order2 = client.post(
        "/api/v1/order", 
        json={
            "direction": "BUY", 
            "ticker": "MEMECOIN", 
            "qty": 2},

        headers={
            "Authorization": f"{token} {user2["api_key"]}",
            "Content-Type": "application/json"}
    )
    assert create_market_order2.status_code == status.HTTP_200_OK

    list_orders2 = client.get(
        "/api/v1/order",
        headers={
            "Authorization": f"{token} {user2["api_key"]}",
            "Content-Type": "application/json"}
    ).json()
    
    assert len(list_orders2) == 1
    assert list_orders2[0]['status'] == "EXECUTED"


    list_orders1 = client.get(
        "/api/v1/order",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    ).json()
    
    assert len(list_orders1) == 1
    assert list_orders1[0]['status'] == "PARTIALLY_EXECUTED"


    user1_balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user1["api_key"]}",
            "Content-Type": "application/json"}
    ).json()
    assert user1_balance["MEMECOIN"] == 0
    assert user1_balance["RUB"] == 200

    user2_balance = client.get(        
        "/api/v1/balance",
        headers={
            "Authorization": f"{token} {user2["api_key"]}",
            "Content-Type": "application/json"}
    ).json()
    assert user2_balance["MEMECOIN"] == 2
    assert user2_balance["RUB"] == 0 # Error 200 != 0