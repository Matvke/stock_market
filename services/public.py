from misc.models import *
from schemas.response import UserResponse, InstrumentResponse
from schemas.request import NewUserRequest
from schemas.internal import UserCreate
from dao.dao import UserDAO, InstrumentDAO
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List


async def register_user(new_user: NewUserRequest, session: AsyncSession) -> UserResponse:
    user_model = UserCreate(
        name=new_user.name,
        role=RoleEnum.USER,
        api_key=f"key-{uuid4()}"
    )
    user = await UserDAO.add(session, user_model)
    return UserResponse.model_validate(user)


async def get_instruments_list(session: AsyncSession) -> List[Instrument] | None:
    instruments = await InstrumentDAO.find_all(session=session)
    return [InstrumentResponse.model_validate(instrument) for instrument in instruments]