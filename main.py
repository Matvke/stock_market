from db_methods import register
from asyncio import run 

new_user_id = run(register(name="Pedro"))
print(f"Готов {new_user_id}")