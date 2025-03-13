from sqlalchemy.ext.asyncio import AsyncSession
from database import connection
from asyncio import run
from models import User, Api_key
from pydantic import BaseModel
from enums import RoleEnum


@connection
async def register(name: str, session: AsyncSession) -> int:  
    new_user = User(name=name, role=RoleEnum.USER)
    session.add(new_user)
    await session.flush()

    new_key = Api_key(user_id=new_user.id, api_key='test')
    session.add(new_key)
    
    await session.commit()
    return {new_user.id, new_key.id}
