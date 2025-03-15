from functools import wraps
from typing import Optional
from sqlalchemy import text
from dao.database import async_session_maker


def connection(isolation_level: Optional[str] = None, commit: bool = True):
    """Декоратор для создания сессий с настройкой изоляции и коммита
    - `isolation_level`: уровень изоляции для транзакции ("SERIALIZABLE", "REPEATABLE READ", "READ COMMITTED").
    - `commit`: если `True`, выполняется коммит после вызова метода."""
    def decorator(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            async with async_session_maker() as session:
                try:
                    if isolation_level:
                        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                    result = await method(*args, session=session ,**kwargs)
                    if commit:
                        await session.commit()
                    return result
                except Exception as e:
                    await session.rollback()
                    raise e
                finally:
                    await session.close()
        return wrapper
    return decorator