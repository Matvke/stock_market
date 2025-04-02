from functools import partial
from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Optional, Annotated
from dao.database import async_session_maker
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status
from misc.db_models import User
from dao.dao import UserDAO
from schemas.request import UserAPIRequest


async def get_db(
        isolation_level: Optional[str] = None,
        commit: bool = True
) -> AsyncGenerator[AsyncSession, None]:
    """Инновационная замена декоратора `@connection`.
    Параметры:
    - isolation_level: `"SERIALIZABLE"`, `"REPEATABLE READ"`, `"READ COMMITTED"`
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
SerializableDbDep = Annotated[AsyncSession, Depends(partial(get_db, isolation_level="SERIALIZABLE"))]

security = HTTPBearer(bearerFormat="TOKEN")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Зависимость для аутентификации по API key"""
    api_key = credentials.credentials
    user = await UserDAO.find_one_or_none(session, filters=UserAPIRequest(api_key=api_key))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return user

CurrentUser = Annotated[User, Depends(get_current_user)]