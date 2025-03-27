from pydantic import BaseModel
from misc.enums import RoleEnum
from uuid import UUID


class UserCreate(BaseModel):
    name: str
    role: RoleEnum
    api_key: str
