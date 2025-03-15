from datetime import datetime
from sqlalchemy import CheckConstraint, ForeignKey, Integer, func, text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from dao.database import Base
from enums import RoleEnum, DirectionEnun, StatusEnum
import re

class User(Base):
    """Таблица пользователей\n
    `__tablename__ = 'users'`\n
    id: int\n
    name: str\n
    role: str\n
    api_key: str"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) # TODO uuid4
    name: Mapped[str] 
    role: Mapped[RoleEnum] = mapped_column(
        default=RoleEnum.USER,
        server_default=text("'USER'")
    )
    api_key: Mapped[str] = mapped_column(String(255), unique=True)

    order: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    balance: Mapped[list["Balance"]] = relationship(
        "Balance",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    buyer_transaction: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="[Transaction.buyer_id]",
        back_populates="buyer"
    )

    seller_transaction: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="[Transaction.seller_id]",
        back_populates="seller"
    )


class Balance(Base):
    """
```user_id: Mapped[int]
ticker: Mapped[str] 
amount: Mapped[int]"""
    __tablename__ = "balances"

    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True) 
    ticker: Mapped[str] = mapped_column(ForeignKey('instruments.ticker'), primary_key=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))

    user: Mapped["User"] = relationship(
        "User",
        back_populates="balance"
    )

    instrument: Mapped["Instrument"] = relationship(
        "Instrument",
        back_populates="balance"
    )


class Instrument(Base):
    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str]

    @validates('ticker')
    def validate_ticker(self, key, ticker):
        if not re.match(r'^[A-Z]{2,10}$', ticker):
            raise ValueError("Ticker must be 2-10 uppercase letters")
        return ticker

    order: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="instrument",
    )

    balance: Mapped[list["Balance"]] = relationship(
        "Balance",
        back_populates="instrument",
        cascade="all, delete-orphan"
    )

    transaction: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="instrument",
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    ticker: Mapped[str] = mapped_column(ForeignKey('instruments.ticker'))
    direction: Mapped[DirectionEnun]
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StatusEnum] = mapped_column(
        default=StatusEnum.NEW, 
        server_default=text("'NEW'")
        )
    filled: Mapped[int]

    user: Mapped["User"] = relationship(
        "User",
        back_populates="order"
    )

    instrument: Mapped["Instrument"] = relationship(
        "Instrument",
        back_populates="order"
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    buyer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ticker: Mapped[str] = mapped_column(ForeignKey('instruments.ticker'))
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())


    buyer: Mapped["User"] = relationship(
        "User",
        foreign_keys=[buyer_id],
        back_populates="buyer_transaction"
    )
    seller: Mapped["User"] = relationship(
        "User",
        foreign_keys=[seller_id],
        back_populates="seller_transaction"
    )

    instrument: Mapped["Instrument"] = relationship(
        "Instrument",
        back_populates="transaction"
    )