from datetime import datetime
from sqlalchemy import ForeignKey, Integer, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from enums import RoleEnum


class User(Base):
    """Таблица пользователей\n
    `__tablename__ = 'users'`\n
    id: int\n
    name: str\n
    role: str\n
    created_at: datetime\n
    updated_at: datetime\n
    Один ко многим с Api_key"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] # TODO Возможно стоит сделать уникальным
    role: Mapped[RoleEnum] = mapped_column(
        default=RoleEnum.USER,
        server_default=text("'USER")
    )
 
    creared_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Один ко многим с Api_key
    keys: Mapped[list["Api_key"]] = relationship(
        "Api_key",
        back_populates="user", # Связь с полем user в Api_key
        cascade="all, delete-orphan" # Каскадное удаление всех ключей при удалении пользователя
    )


class Api_key(Base):
    """Таблица с API ключами пользователей\n
    `__tablename__ = 'keys'` \n
    `id = int`\n
    `user_id = int`\n
    `api_key = str`\n
    `created_at: datetime`\n
    `updated_at: datetime`\n
    Многие к одному с `User` по полю `user_id`"""
    
    __tablename__ = "keys"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    api_key: Mapped[str]

    creared_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Многие к одному с User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="keys" # Связь с полем keys в User
    )

# TODO инструменты, торги