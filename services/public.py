from misc.models import *
from schemas.response import UserResponse
from schemas.request import NewUserRequest
from schemas.internal import UserCreate
from dao.dao import UserDAO
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession


async def register_user(new_user: NewUserRequest, session: AsyncSession) -> UserResponse:
    user_model = UserCreate(
        name=new_user.name,
        role=RoleEnum.USER,
        api_key=f"key-{uuid4()}"
    )
    user = await UserDAO.add(session, user_model)
    return UserResponse.model_validate(user)