import logging
import os
from typing import List

import sqlalchemy as sqla
from sqlalchemy import ForeignKey, Index, JSON, BigInteger
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
)
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.engine import Engine
from sqlalchemy import event
from decimal import Decimal
import datetime
from fractions import Fraction
from math import ceil, floor
from typing import Optional, List

import ipdb


DATABASE_URI = os.environ.get("DATABASE_URI", "sqlite+pysqlite:///db.sqlite")
if DATABASE_URI.startswith("sqlite"):

    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """This makes sure that sqlite will respect cascade delete"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_engine(connect_string: str, echo: bool = False) -> sqla.Engine:
    return sqla.create_engine(connect_string, echo=echo, poolclass=sqla.pool.QueuePool)


_ENGINE = create_engine(DATABASE_URI, echo=False)


########################################################################################
#                                          DB Schema                                   #
########################################################################################


class Base(DeclarativeBase):
    pass


class UTxO(Base):
    """
    Unspent UTxOs. These are stored so that we can calculate the batcher profits.
    """

    __tablename__ = "UTxO"

    id: Mapped[str] = mapped_column(primary_key=True, index=True)  # Txhash#output_idx

    owner: Mapped[str]  # Address that owns this UTxO
    value: Mapped[dict] = mapped_column(JSON)  # Dictionary of assets

    created_slot: Mapped[int] = mapped_column(BigInteger)
    spent_slot: Mapped[int] = mapped_column(BigInteger, nullable=True)

    block_hash: Mapped[str] = mapped_column(
        index=True
    )  # Used to sync ogmios. Corresponds to block containining transaction that creates UTxO

    def __repr__(self) -> str:
        return self.id


class Batcher(Base):
    """
    Represents a single batcher entity
    """

    __tablename__ = "Batcher"

    # TODO maybe add some stats here

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    addresses = relationship("BatcherAddress", back_populates="batcher")
    transactions = relationship("Transaction", back_populates="batcher")


class BatcherAddress(Base):
    """
    Represents a batcher address (each batcher may have multiple wallets)
    """

    __tablename__ = "BatcherAddress"

    address: Mapped[str] = mapped_column(primary_key=True)
    batcher_id: Mapped[int] = mapped_column(ForeignKey(Batcher.id))
    batcher = relationship("Batcher", back_populates="addresses")


class Order(Base):
    """
    Represents an order. Includes info from the UTxO and datum
    """

    __tablename__ = "Order"

    id: Mapped[str] = mapped_column(primary_key=True)  # Txhash#output_idx
    sender: Mapped[str]  # Address that receives funds if cancelled
    recipient: Mapped[str]  # Address that receives funds if fulfilled
    slot: Mapped[int] = mapped_column(
        BigInteger
    )  # Slot in which the order was placed (UTxO was created)
    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("Transaction.id", ondelete="SET NULL", onupdate="cascade"),
        nullable=True,
    )
    transaction = relationship("Transaction", back_populates="orders")


class Transaction(Base):
    """
    Represents a transaction
    """

    __tablename__ = "Transaction"

    id: Mapped[int] = mapped_column(primary_key=True)
    orders: Mapped[List[Order]] = relationship(back_populates="transaction")
    batcher_id: Mapped[int] = mapped_column(ForeignKey("Batcher.id"), nullable=True)
    batcher: Mapped[Batcher] = relationship(back_populates="transactions")
    ada_profit: Mapped[int] = mapped_column(
        BigInteger
    )  # Net ada difference between inputs and outputs. TODO may not be necessary
    network_fee: Mapped[int] = mapped_column(BigInteger)
    equivalent_ada: Mapped[int] = mapped_column(
        BigInteger
    )  # Net revenue converted to ada at current prices
    net_assets: Mapped[dict] = mapped_column(JSON)
    slot: Mapped[int] = mapped_column(BigInteger)
    tx_hash: Mapped[str]


########################################################################################
#                      Helpers to get (and potentially create) Rows                    #
########################################################################################


def get_max_slot_block_and_index() -> tuple:
    """
    Return the largest slot-number and tx-index with an order
    in the database.
    """
    stmt = (
        sqla.select(UTxO.created_slot, UTxO.block_hash)
        .order_by(UTxO.created_slot.desc(), UTxO.block_hash.desc())
        .limit(1)
    )
    with Session(_ENGINE) as session:
        res = session.execute(stmt).first()
        session.rollback()
    if not res:
        return 0, ""
    return res  # type: ignore


Base.metadata.create_all(_ENGINE)
