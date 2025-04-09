from fastapi import FastAPI
from api.public import public_router
from api.balance import balance_router
from api.order import order_router


app = FastAPI()
app.include_router(public_router)
app.include_router(balance_router)
app.include_router(order_router)