from db_methods import register, get_instruments_list, get_balances, get_user_key
from asyncio import run 

# new_user_id = run(register(user_data={"name":"San"}))
# print(f"Готов {new_user_id}")

# instruments = run(get_instruments_list())
# for i in instruments:
#     print(i.to_dict())

# key = run(get_user_key(user_data={"api_key": "TOKEN 1"}))
# print(key)

# balances = run(get_balances(user_data={"api_key":"TOKEN"}))
# for i in balances:
#     print(i.to_dict())