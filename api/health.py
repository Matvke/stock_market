from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text
from datetime import datetime
from dependencies import get_db, get_engine

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


# 3. Проверка активных сессий (для отладки)
@health_router.get("/active-sessions")
async def show_active_sessions(engine: AsyncEngine = Depends(get_engine)):
    """Показывает активные сессии (только для отладки)"""
    if not hasattr(engine.pool, '_checkedout'):
        return {"message": "Session tracking not supported for this pool type"}
    
    return {
        "checked_out_connections": len(engine.pool._checkedout),
        "pool_size": engine.pool.size(),
        "overflow": engine.pool.overflow()
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
    