import logging
import os
from typing import List

import sqlalchemy as sqla
from cardano_python_utils.classes import Asset, Token, LOVELACE, ShelleyAddress  # type: ignore
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

    # There can be more swaps in a single tx, this corresponds to one swap
    # Therefore we require only that (tx hash + output utxo idx) is unique
    # __table_args__ = (
    #     UniqueConstraint("hash", "output_idx", name="unique_utxo"),
    #     Index("utxo_by_hash_and_idx", "hash", "output_idx"),
    # )

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
    batcher_id: Mapped[int] = mapped_column(
        ForeignKey("Batcher.id"),
    )
    batcher: Mapped[Batcher] = relationship(back_populates="transactions")
    ada_revenue: Mapped[int] = mapped_column(
        BigInteger
    )  # Net ada difference between inputs and outputs. TODO may not be necessary
    network_fee: Mapped[int] = mapped_column(BigInteger)
    equivalent_ada: Mapped[int] = mapped_column(
        BigInteger
    )  # Net revenue converted to ada at current prices
    net_assets: Mapped[dict] = mapped_column(JSON)
    slot: Mapped[int] = mapped_column(BigInteger)


# class Order(Base):
#     __tablename__ = "Order"

#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     # Smart contract version eg. v1 orderbook, v2 orderbook, staking
#     protocol: Mapped[str] = mapped_column()
#     tx_id: Mapped[int] = mapped_column(
#         ForeignKey(Tx.id, ondelete="cascade", onupdate="cascade"), index=True
#     )

#     # how much of the asked amount was received so far
#     fulfilled_amount: Mapped[Decimal]
#     # how much of the bid amount was paid so far
#     paid_amount: Mapped[Decimal]
#     batcher_fee: Mapped[Decimal]
#     # Part of fee that was paid until now in case of partial matches
#     # paid_fee: Mapped[Decimal]

#     sender_pkh: Mapped[str]
#     sender_skh: Mapped[str]
#     beneficiary_pkh: Mapped[str]
#     beneficiary_skh: Mapped[str]

#     # ask = to, bid = from
#     ask_token: Mapped[str] = mapped_column(index=True)
#     bid_token: Mapped[str] = mapped_column(index=True)
#     ask_amount: Mapped[Decimal]
#     bid_amount: Mapped[Decimal]

#     batcher_pkh: Mapped[str] = mapped_column(index=True)
#     batcher_skh: Mapped[str] = mapped_column(index=True)

#     # Additional batcher addresses?

#     # To calculate how quickly the batcher fills the order
#     placed_slot_no: Mapped[int] = mapped_column(BigInteger, index=True)
#     fulfilled_slot_no: Mapped[int] = mapped_column(BigInteger, index=True)

#     # By using the following relationship we avoid adding a new table
#     cancellation_id: Mapped[int] = mapped_column(
#         ForeignKey("Cancellation.id", ondelete="SET NULL", onupdate="cascade"),
#         index=True,
#         nullable=True,
#     )

#     full_match_id: Mapped[int] = mapped_column(
#         ForeignKey("FullMatch.id", ondelete="SET NULL", onupdate="cascade"),
#         index=True,
#         nullable=True,
#     )

#     tx: Mapped[Tx] = relationship(back_populates="order")
#     partial_matches: Mapped[List["PartialMatch"]] = relationship(
#         back_populates="order", cascade="all, delete", order_by="PartialMatch.slot_no"
#     )
#     cancellation: Mapped["Cancellation"] = relationship(back_populates="order")
#     full_match: Mapped["FullMatch"] = relationship(back_populates="order")

#     # Avoids changing the schema if we want to parse something new from the trade UTxO/datum
#     dex_specifics: Mapped[dict] = mapped_column(JSON, nullable=True)

#     def get_current_utxo(self):
#         """returns the most recent orderbook utxo - either original or partial match"""
#         if len(self.partial_matches) > 0:
#             return self.partial_matches[-1].new_utxo
#         return self.tx

#     # def get_status(self) -> OrderStatus:
#     #     if self.cancellation_id is not None:
#     #         return OrderStatus.CANCELLED
#     #     if self.full_match_id is not None:
#     #         return OrderStatus.FULFILLED
#     #     if len(self.partial_matches) > 0:
#     #         return OrderStatus.PARTIAL_MATCH
#     #     return OrderStatus.OPEN

#     # def finalized_at(self) -> int | None:
#     #     if self.cancellation is not None:
#     #         return util.slot_datestring(self.cancellation.slot_no)
#     #     if self.full_match is not None:
#     #         return util.slot_datestring(self.full_match.slot_no)
#     #     return None

#     __table_args__ = (
#         Index("order_sender_pkh", "sender_pkh"),
#         Index("order_sender_skh", "sender_skh"),
#     )


# class PartialMatch(Base):
#     __tablename__ = "PartialMatch"
#     id: Mapped[int] = mapped_column(primary_key=True)
#     order_id: Mapped[int] = mapped_column(
#         ForeignKey(Order.id, ondelete="cascade", onupdate="cascade")
#     )
#     new_utxo_id: Mapped[str] = mapped_column(
#         ForeignKey(Tx.id, ondelete="cascade", onupdate="cascade")
#     )
#     order: Mapped[Order] = relationship(
#         back_populates="partial_matches",
#         cascade="all, delete",
#         foreign_keys=[order_id],
#         uselist=False,
#     )
#     new_utxo: Mapped[Tx] = relationship(
#         cascade="all, delete", foreign_keys=[new_utxo_id], uselist=False
#     )
#     matched_amount: Mapped[Decimal]  # not cumulative
#     paid_amount: Mapped[Decimal]  # not cumulative
#     slot_no: Mapped[int]
#     __table_args__ = (
#         UniqueConstraint("order_id", "new_utxo_id", name="unique_utxo_order_pm_pair"),
#         Index("partial_match_by_order_utxo", "order_id", "new_utxo_id"),
#         Index("partial_match_by_order_slot_no", "order_id", "slot_no"),
#     )


# class Cancellation(Base):
#     __tablename__ = "Cancellation"
#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     order: Mapped[Order] = relationship(
#         back_populates="cancellation", cascade="all, delete", uselist=False
#     )
#     # block in which the match occurred (kept here since we don't track the utxo)
#     slot_no: Mapped[int]
#     tx_hash: Mapped[str]


# class FullMatch(Base):
#     __tablename__ = "FullMatch"
#     id: Mapped[int] = mapped_column(primary_key=True, index=True)
#     order: Mapped[Order] = relationship(
#         back_populates="full_match", cascade="all, delete", uselist=False
#     )
#     matched_amount: Mapped[Decimal]  # not cumulative
#     paid_amount: Mapped[Decimal]  # not cumulative
#     # block in which the match occurred (kept here since we don't track the utxo)
#     slot_no: Mapped[int]
#     tx_hash: Mapped[str]


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
