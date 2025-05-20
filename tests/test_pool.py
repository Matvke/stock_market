import asyncio
import traceback
import httpx
import random
import string

BASE_URL = "http://localhost:8000"

def handle_exception(exc_type, exc_value, exc_traceback):
    # Получаем последний фрейм ошибки
    last_frame = exc_traceback
    while last_frame.tb_next:
        last_frame = last_frame.tb_next
    
    # Извлекаем информацию о месте ошибки
    filename = last_frame.tb_frame.f_code.co_filename
    line_no = last_frame.tb_lineno
    line = traceback.linecache.getline(filename, line_no).strip()
    
    print(f"Ошибка: {exc_value}\nФайл: {filename}, строка {line_no}: {line}")

# sys.excepthook = handle_exception


def random_username():
    return "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def register_user(client: httpx.AsyncClient) -> str:
    payload = {
        "name": random_username(),
    }
    resp = await client.post(f"{BASE_URL}/api/v1/public/register", json=payload)
    resp.raise_for_status()
    return resp.json()


async def delete_user(client: httpx.AsyncClient, id):
    headers = {"Authorization": "TOKEN key-c5e07b4b-35c8-43ad-887a-6d9cdc1b172c"}
    resp = await client.delete(f"{BASE_URL}/api/v1/admin/user/{id}", headers=headers)
    resp.raise_for_status()


async def add_instrument(client: httpx.AsyncClient):
    headers = {"Authorization": "TOKEN key-c5e07b4b-35c8-43ad-887a-6d9cdc1b172c"}
    body = {
        "name": "TEST",
        "ticker": "TEST"
    }
    resp = await client.post(f"{BASE_URL}/api/v1/admin/instrument", headers=headers, json=body)
    resp.raise_for_status()   


async def delete_instrument(client: httpx.AsyncClient):
    headers = {"Authorization": "TOKEN key-c5e07b4b-35c8-43ad-887a-6d9cdc1b172c"}
    resp = await client.delete(f"{BASE_URL}/api/v1/admin/instrument/TEST", headers=headers)
    resp.raise_for_status()


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
        "amount": 100
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


async def user_create_buy_test_market_order(client: httpx.AsyncClient, token):
    headers = {"Authorization": f"TOKEN {token}"}
    body = {
        "direction": "BUY",
        "ticker": "TEST",
        "qty": 1,
    }
    resp = await client.post(f"{BASE_URL}/api/v1/order", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


async def user_create_sell_test_market_order(client: httpx.AsyncClient, token):
    headers = {"Authorization": f"TOKEN {token}"}
    body = {
        "direction": "SELL",
        "ticker": "TEST",
        "qty": 1,
    }
    resp = await client.post(f"{BASE_URL}/api/v1/order", headers=headers, json=body)
    resp.raise_for_status()
    return resp.json()


async def get_order(client: httpx.AsyncClient, id, token):
    headers = {"Authorization": f"TOKEN {token}"}
    resp = await client.get(f"{BASE_URL}/api/v1/order/{id}", headers=headers)
    resp.raise_for_status()
    return resp.json()


async def get_list_order(client: httpx.AsyncClient):
    headers = {"Authorization": "TOKEN key-c5e07b4b-35c8-43ad-887a-6d9cdc1b172c"}
    resp = await client.get(f"{BASE_URL}/api/v1/order", headers=headers)
    resp.raise_for_status()
    return resp.json()


async def user_workflow(client, token, user_id):
    try:
        for _ in range(5):
            tasks = [
                check_balance(client, token),
                user_update_balance(client, user_id, ticker='RUB'),
                user_update_balance(client, user_id, ticker='TEST'),
                user_create_sell_test_limit_order(client, token),
                user_create_buy_test_limit_order(client, token),
                # user_create_buy_test_market_order(client, token),
                # user_create_sell_test_market_order(client, token),
                get_list_order(client),
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Обрабатываем заказы отдельно (если успешно создались)
            for result in results:
                if isinstance(result, dict) and 'order_id' in result:
                    await get_order(client, id=result['order_id'], token=token)

    except Exception as e:
        raise e


async def stress_test(concurrent_users: int):
    print(f"Running stress test with {concurrent_users} concurrent users...")
    async with httpx.AsyncClient(
    timeout=10.0,     
        limits=httpx.Limits(
            max_connections=200,
            max_keepalive_connections=100
    )) as client:
        try:
            # Добавляем инструмент один раз перед всеми пользователями
            await delete_instrument(client)

            await add_instrument(client)
            
            # Регистрируем всех пользователей
            users = []
            for _ in range(concurrent_users):
                user = await register_user(client)
                users.append(user)
            
            # Запускаем все workflow параллельно
            await asyncio.gather(*(
                user_workflow(client, user["api_key"], user['id'])
                for user in users
            ))
            
        finally:
            # Удаляем всех пользователей и инструмент
            # await asyncio.gather(*(
            #     delete_user(client, user['id'])
            #     for user in users
            # ))
            # await delete_instrument(client)
            
            # Проверяем статус пула
            resp = await client.get(f"{BASE_URL}/api/v1/health/pool-status")
            print(resp.json())


if __name__ == "__main__":
    asyncio.run(stress_test(300))
