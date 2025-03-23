from db_methods import *
from schemas import InstrumentPydantic, Balance_Output_Pydantic, Balance_Find_Pydantic, Show_Order_Pydantic, UserPydantic
import asyncio

async def main():
    # new_user = await register(user_data={"name":"Francisco"})
    # print(f"Готов {new_user}")

    # instruments = await get_instruments_list()
    # for i in instruments:
    #     ip = InstrumentPydantic.model_validate(i) 
    #     print(ip)

    # balances = await get_balances(user_data={"api_key": "key-f3668576-d098-4dc3-b476-6dcf4c863da3"})
    # for b in balances:
    #     bp = Balance_Output_Pydantic.model_validate(b)
    #     print(bp)

    # temp = await update_balance(user_data={"api_key": "key-f3668576-d098-4dc3-b476-6dcf4c863da3", "ticker": "PRR", "amount": "50"})
    # print(temp)

    # temp1 = await find_balance(user_data={"user_id": "70d7e92a-d2d3-4fec-8c87-a0e6bd5098ac", "ticker": 'PRR'})
    # print(Balance_Output_Pydantic.model_validate(temp1))

    # antonio_sell_hdg = await create_order(user_data={"api_key": "key-f3668576-d098-4dc3-b476-6dcf4c863da3", "ticker": "HDG", "direction": "SELL", "qty": 5, "price": 12})
    # print(antonio_sell_hdg)
    # antonio_sell_prr = await create_order(user_data={"api_key": "key-f3668576-d098-4dc3-b476-6dcf4c863da3", "ticker": "PRR", "direction": "SELL", "qty": 50, "price": 5})
    # print(antonio_sell_prr)

    # jose_buy_prr_without_balance = await create_order(user_data={"api_key": "key-a0ec9b50-64fb-4e6d-b606-52a47e91959c", "ticker": "PRR", "direction": "BUY", "qty": 1, "price": 5})
    # print(jose_buy_prr_without_balance)

    # jose_buy_prr_alot = await create_order(user_data={"api_key": "key-a0ec9b50-64fb-4e6d-b606-52a47e91959c", "ticker": "HDG", "direction": "BUY", "qty": 5, "price": 12})
    # print(jose_buy_prr_alot)

    jose_sell_hdg = await create_order(user_data={"api_key": "key-a0ec9b50-64fb-4e6d-b606-52a47e91959c", "ticker": "HDG", "direction": "SELL", "qty": 20, "price": 13})
    print(jose_sell_hdg)

    antonio_buy_hdg = await create_order(user_data={"api_key": "key-f3668576-d098-4dc3-b476-6dcf4c863da3", "ticker": "HDG", "direction": "BUY", "qty": 5, "price": 13})
    print(antonio_buy_hdg)

    # orders = await get_list_orders(user_data={"api_key": "key-a0ec9b50-64fb-4e6d-b606-52a47e91959c"})
    # for o in orders:
    #     print(Show_Order_Pydantic.model_validate(o))

    # order = await get_order({"api_key": "key-a0ec9b50-64fb-4e6d-b606-52a47e91959c", "order_id": 'b6e0caa5-de76-4761-b72e-4ac3e4760d5d'})
    # print(Show_Order_Pydantic.model_validate(order))

    # delete = await cancel_order({"api_key": "TOKEN", "order_id": 7})
    # print(delete)

    # inasd = await add_instrument({"api_key": "key-d1ae6ee0-7e97-49a3-9967-be896cd26c2a", "ticker": "HDG", "name": "HEDGEHOG"})
    # print(inasd)

    # faopaf = await delete_instrument({"api_key": "key-d1ae6ee0-7e97-49a3-9967-be896cd26c2a", "ticker": "CHCK", "name": "CHICKEN"})
    # print(faopaf)

    # orderbook = await get_orderbook(user_data={"ticker": "PRR", "limit": 4})
    # for o in orderbook:
    #     print(Show_Order_Pydantic.model_validate(o))

asyncio.run(main())