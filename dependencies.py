from fastapi import Depends, Request, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Annotated
from dao.database import async_session_maker
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security.utils import get_authorization_scheme_param
from misc.db_models import User
from dao.dao import UserDAO
from misc.enums import RoleEnum
from schemas.request import UserAPIRequest


token = "token"

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

DbDep = Annotated[AsyncSession, Depends(get_db)]


class HTTPToken(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        auth = request.headers.get("Authorization")
        scheme, param = get_authorization_scheme_param(auth)

        if not auth or scheme.lower() != token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Invalid authentication credentials expected {token}"
                )
            else:
                return None

        return HTTPAuthorizationCredentials(scheme=scheme, credentials=param)
    

security = HTTPToken()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Зависимость для аутентификации по API key"""
    async with session.begin():
        api_key = credentials.credentials
        user = await UserDAO.find_one_or_none(session, filters=UserAPIRequest(api_key=api_key))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User with {api_key} not found"
            )
        return user


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_db)
) -> User:
    async with session.begin():
        api_key = credentials.credentials
        admin = await UserDAO.find_one_or_none(session, filters=UserAPIRequest(api_key=api_key, role=RoleEnum.ADMIN))
        if not admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Admin with {api_key} not found.")
        return admin


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentAdmin = Annotated[User, Depends(get_current_admin)]