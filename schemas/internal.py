from pydantic import BaseModel, field_validator
from misc.enums import RoleEnum
from uuid import UUID


class UserCreate(BaseModel):
    name: str
    role: RoleEnum
    api_key: str  # Формат "key-<UUID>"

    @field_validator("name")
    def validate_name(cls, v):
        if len(v) < 3:
            raise ValueError("The name must be longer than 3 letters")
        return v
    


    @field_validator('api_key')
    def validate_api_key(cls, v):
        if not v.startswith('key-'):
            raise ValueError("API key must start with 'key-'")
        
        uuid_part = v[4:]  # Отрезаем 'key-'
        try:
            UUID(uuid_part)  # Проверяем, что это валидный UUID
        except ValueError:
            raise ValueError("Invalid UUID part in API key")
        
        return v
