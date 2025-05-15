import asyncio
import httpx
import random
import string

BASE_URL = "http://localhost:8000"

def random_username():
    return "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def register_user(client: httpx.AsyncClient) -> str:
    payload = {
        "name": random_username(),
    }
    resp = await client.post(f"{BASE_URL}/api/v1/public/register", json=payload)
    resp.raise_for_status()
    return resp.json()


async def check_balance(client: httpx.AsyncClient, token: str):
    headers = {"Authorization": f"TOKEN {token}"}
    resp = await client.get(f"{BASE_URL}/api/v1/balance", headers=headers)
    resp.raise_for_status()
    return resp.json()


async def user_update_balance(client: httpx.AsyncClient, id, ticker):
    headers = {"Authorization": "TOKEN key-c5e07b4b-35c8-43ad-887a-6d9cdc1b172c"}
    body = {
        "user_id": id,
        "ticker": ticker,
        "amount": 10
    }
    resp = await client.post(f"{BASE_URL}/api/v1/admin/balance/deposit", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


async def user_create_sell_test_limit_order(client: httpx.AsyncClient, token):
    headers = {"Authorization": f"TOKEN {token}"}
    body = {
        "direction": "SELL",
        "ticker": "TEST",
        "qty": 1,
        "price": 1
    }
    resp = await client.post(f"{BASE_URL}/api/v1/order", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


async def user_create_buy_test_limit_order(client: httpx.AsyncClient, token):
    headers = {"Authorization": f"TOKEN {token}"}
    body = {
        "direction": "BUY",
        "ticker": "TEST",
        "qty": 1,
        "price": 2
    }
    resp = await client.post(f"{BASE_URL}/api/v1/order", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


async def user_workflow():
    async with httpx.AsyncClient(timeout=10.0) as client:
        user = await register_user(client)
        token = user["api_key"]
        id = user['id']
        for _ in range(5):
            await check_balance(client, token)
            await user_update_balance(client, id, ticker='RUB')
            await user_update_balance(client, id, ticker='TEST')
            await user_create_sell_test_limit_order(client, token)
            await user_create_buy_test_limit_order(client, token)


async def stress_test(concurrent_users: int):
    print(f"Running stress test with {concurrent_users} concurrent users...")
    await asyncio.gather(*(user_workflow() for _ in range(concurrent_users)))
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{BASE_URL}/api/v1/health/pool-status")
        print(resp.json())

if __name__ == "__main__":
    asyncio.run(stress_test(50))
