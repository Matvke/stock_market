from datetime import datetime
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
    format="%(levelname)s (%(asctime)s):      %(message)s",
    datefmt="%d-%m-%Y %H:%M:%S",
    handlers=[
        logging.FileHandler('http_requests.log', encoding='utf-8'),  # Пишет логи в файл
        logging.StreamHandler()  # Выводит логи в консоль
    ])

app = FastAPI(lifespan=lifespan)


app.include_router(public_router)
app.include_router(balance_router)
app.include_router(order_router)
app.include_router(admin_router)
app.include_router(health_router)


logger = logging.getLogger("uvicorn.error")

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    
    # Пропускаем запросы к самому эндпоинту логов
    if request.url.path == "/api/logs":
        response = await call_next(request)
        return response
    
    request_info = {
        "method": request.method,
        "timestamp": datetime.now().isoformat(),
        "url": str(request.url),
        "headers": dict(request.headers),
        "client": request.client.host if request.client else None,
    }
    
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {request_info} - Error: {str(e)}")
        raise e
    
    
    request_info.update({
        "status_code": response.status_code
    })
    
    # logger.info(f"Request processed: {request_info}")
    
    return response
