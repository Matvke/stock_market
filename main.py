import sys
import traceback
from fastapi import FastAPI
from api.public import public_router
from api.balance import balance_router
from api.order import order_router
from api.admin import admin_router
from api.health import health_router
from contextlib import asynccontextmanager
import asyncio
from dao.database import async_session_maker
from services.engine import matching_engine
from services.matching import run_matching_engine
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


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


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:      %(message)s       (%(asctime)s)",
    datefmt="%d-%m-%Y %H:%M:%S")

logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)

app = FastAPI(lifespan=lifespan)


app.include_router(public_router)
app.include_router(balance_router)
app.include_router(order_router)
app.include_router(admin_router)
app.include_router(health_router)


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

sys.excepthook = handle_exception

logger = logging.getLogger("uvicorn.error")


class LogErrorResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code >= 400:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
                
            async def new_body():
                yield body
            response.body_iterator = new_body()

            logger.warning(f"{request.method} {request.url.path} -> {response.status_code}: {body.decode('utf-8')}")
        return response

    
app.add_middleware(LogErrorResponseMiddleware)
