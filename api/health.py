from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text
from datetime import datetime
from dependencies import get_db, get_engine, DbDep
from dao.dao import UserDAO, OrderDAO, BalanceDAO, InstrumentDAO
from fastapi.responses import FileResponse
from pathlib import Path

health_router = APIRouter(prefix="/api/v1/health", tags=["health"])


# 1. Проверка доступности БД
@health_router.get("/db-check")
async def database_health_check(session: AsyncSession = Depends(get_db)):
    """Проверяет доступность базы данных"""
    try:
        result = await session.execute(text("SELECT 1"))
        return {"status": "healthy", "db_response": result.scalar()}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# 2. Статус пула соединений
@health_router.get("/pool-status")
async def pool_status(engine: AsyncEngine = Depends(get_engine)):
    """Возвращает статистику пула соединений"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "timeout": pool.timeout(),
        "recycle": pool._recycle if hasattr(pool, '_recycle') else None,
    }


# 4. Проверка времени отклика БД
@health_router.get("/db-response-time")
async def db_response_time(session: AsyncSession = Depends(get_db)):
    """Измеряет время отклика базы данных"""
    start_time = datetime.now()
    await session.execute(text("SELECT 1"))
    response_time = (datetime.now() - start_time).total_seconds() * 1000
    return {"response_time_ms": round(response_time, 2)}


# 5. Проверка долгих транзакций
@health_router.get("/long-transactions")
async def check_long_transactions(engine: AsyncEngine = Depends(get_engine)):
    """Проверяет наличие долгих транзакций (PostgreSQL specific)"""
    query = """
    SELECT pid, now() - xact_start AS duration, query 
    FROM pg_stat_activity 
    WHERE state = 'active' AND xact_start IS NOT NULL
    ORDER BY duration DESC;
    """
    
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(query))
            return {"transactions": [dict(row) for row in result.mappings()]}
    except Exception as e:
        return {"error": str(e), "note": "This endpoint works only with PostgreSQL"}


# 6. Проверка блокировок
@health_router.get("/locks")
async def check_locks(engine: AsyncEngine = Depends(get_engine)):
    """Показывает текущие блокировки (PostgreSQL specific)"""
    query = """
    SELECT locktype, relation::regclass, mode, pid 
    FROM pg_locks 
    WHERE pid != pg_backend_pid();
    """
    
    async with engine.connect() as conn:
        result = await conn.execute(text(query))
        return {"locks": [dict(row) for row in result.mappings()]}


@health_router.get("/tables")
async def get_db(session: DbDep, limit=40):
    res = {}
    res['users'] = await UserDAO.find_all(session=session, limit=limit)
    res['orders'] = await OrderDAO.find_all(session=session, limit=limit)
    res['balances'] = await BalanceDAO.find_all(session=session, limit=limit)
    res['instruments'] = await InstrumentDAO.find_all(session=session, limit=limit)

    return res



@health_router.get("/api/logs", response_class=FileResponse)
async def get_request_logs():
    """
    Возвращает файл с логами HTTP-запросов
    """
    log_file = Path('http_requests.log')
    
    if not log_file.exists():
        return []
    
    return FileResponse(
        path=log_file,
        filename="http_requests.log",
        media_type="text/plain"
    )