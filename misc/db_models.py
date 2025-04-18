from datetime import datetime
from sqlalchemy import UUID, ForeignKey, Integer, func, text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates
from dao.database import Base
from misc.enums import RoleEnum, DirectionEnum, StatusEnum, OrderEnum, VisibilityEnum
import re
import uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[RoleEnum] = mapped_column(
        default=RoleEnum.USER,
        server_default=text("'USER'")
    )
    api_key: Mapped[str] = mapped_column(String(255), unique=True)
    visibility: Mapped[VisibilityEnum] = mapped_column(default=VisibilityEnum.ACTIVE, server_default=text("'ACTIVE'"))

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
    __tablename__ = "balances"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), primary_key=True) 
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
    name: Mapped[str] = mapped_column(String(255))
    visibility: Mapped[VisibilityEnum] = mapped_column(default=VisibilityEnum.ACTIVE, server_default=text("'ACTIVE'"))

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'))
    ticker: Mapped[str] = mapped_column(ForeignKey('instruments.ticker'))
    direction: Mapped[DirectionEnum]
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[StatusEnum] = mapped_column(
        default=StatusEnum.NEW, 
        server_default=text("'NEW'")
        )
    filled: Mapped[int] = mapped_column(Integer, nullable=True, default=0, server_default=text("0"))
    order_type: Mapped[OrderEnum] = mapped_column(default=OrderEnum.LIMIT)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())

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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
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