from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Optional, Annotated
from dao.database import async_session_maker


async def get_db(
        isolation_level: Optional[str] = None,
        commit: bool = True
) -> AsyncGenerator[AsyncSession, None]:
    """Инновационная замена декоратора `@connection`.
    Параметры:
    - isolation_level: "SERIALIZABLE", "REPEATABLE READ", "READ COMMITTED
    - commited: Автоматический коммит при успехе"""
    async with async_session_maker() as session:
        try:
            if isolation_level:
                await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            yield session
            if commit:
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbDep = Annotated[AsyncSession, Depends(get_db)]
SerializableDbDep = Annotated[AsyncSession, Depends(lambda: get_db(isolation_level="SERIALIZABLE"))]