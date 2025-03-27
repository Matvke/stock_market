from pydantic import BaseModel, ConfigDict
from misc.enums import *


class UserResponse(BaseModel):
    id: str
    name: str
    role: RoleEnum
    api_key: str

    model_config = ConfigDict(from_attributes=True)