from pydantic import BaseModel


class NewUserRequest(BaseModel):
    name: str