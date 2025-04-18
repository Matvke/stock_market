from fastapi import FastAPI
from api.public import public_router
from api.balance import balance_router
from api.order import order_router
from api.admin import admin_router
from contextlib import asynccontextmanager
import asyncio
from dao.database import async_session_maker
from services.engine import matching_engine
from services.matching import run_matching_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session_maker() as session:
        await matching_engine.startup(session)

    task = asyncio.create_task(run_matching_engine(matching_engine, async_session_maker))

    yield

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)
app.include_router(public_router)
app.include_router(balance_router)
app.include_router(order_router)
app.include_router(admin_router)