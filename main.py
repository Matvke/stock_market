from db_methods import register, get_instruments_list, get_balances, get_user_id
from schemas import InstrumentPydantic, BalancePydantic
import asyncio

async def main():
    new_user = await register(user_data={"name":"Gustavo"})
    print(f"Готов {new_user}")

    # instruments = await get_instruments_list()
    # for i in instruments:
    #     ip = InstrumentPydantic.model_validate(i) # Валидация
    #     print(ip)

    # balances = await get_balances(user_data={"api_key": "TOKEN"})
    # for b in balances:
    #     bp = BalancePydantic.model_validate(b)
    #     print(bp)


asyncio.run(main())