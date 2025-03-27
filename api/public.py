from fastapi import APIRouter
from typing import List

from dependencies import DbDep
from schemas.request import NewUserRequest
from schemas.response import UserResponse, InstrumentResponse
from services.public import register_user, get_instruments_list


router = APIRouter(prefix="/api/v1/public")

@router.post("/register", response_model=UserResponse)
async def api_register_user(
    new_user: NewUserRequest,
    session: DbDep
):
    return await register_user(new_user, session)


@router.get("/instrument", response_model=List[InstrumentResponse])
async def api_get_instruments(session: DbDep):
    return await get_instruments_list(session)