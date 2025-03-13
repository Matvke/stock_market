import enum


class RoleEnum(str, enum.Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'