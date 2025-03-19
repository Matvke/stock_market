from db_methods import *
from schemas import InstrumentPydantic, Balance_Output_Pydantic, Balance_Find_Pydantic, Show_Order_Pydantic
import asyncio

async def main():
    # new_user = await register(user_data={"name":"Gustavo"})
    # print(f"Готов {new_user}")

    # instruments = await get_instruments_list()
    # for i in instruments:
    #     ip = InstrumentPydantic.model_validate(i) # Валидация
    #     print(ip)

    # balances = await get_balances(user_data={"api_key": "TOKEN"})
    # for b in balances:
    #     bp = Balance_Output.model_validate(b)
    #     print(bp)

    # temp = await update_balance(user_data={"api_key": "TOKEN 1", "ticker": "PRR", "amount": "20"})
    # print(temp)

    # temp1 = await find_balance(user_data={"user_id": "1", "ticker": 'ELPH'})
    # print(Balance_Find_Pydantic.model_validate(temp1))

    # new_order = await create_order(user_data={"api_key": "TOKEN", "ticker": "PRR", "direction": "SELL", "qty": 1, "price": 1})
    # print(new_order)
    
    # orders = await get_list_orders(user_data={"api_key": "TOKEN"})
    # for o in orders:
    #     print(Show_Order_Pydantic.model_validate(o))

    order = await get_order({"api_key": "TOKEN", "order_id": 1})
    print(Show_Order_Pydantic.model_validate(order))

asyncio.run(main())