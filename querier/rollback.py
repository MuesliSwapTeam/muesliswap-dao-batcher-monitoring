import logging
import sqlalchemy as sqla
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import ipdb
from common.db import (
    _ENGINE,
    UTxO,
    Order,
    get_max_slot_block_and_index,
)


# TODO: set this to cardano security parameter
MAX_ALLOWED_ROLLBACK = 2 * 86400 / 20  # rollback at most 2 days of blocks
_LOGGER = logging.getLogger(__name__)


class RollbackHandler:
    def __init__(self):
        self.slot, self.block_hash = get_max_slot_block_and_index()
        self.original_slot = self.slot
        _LOGGER.warning(f"Starting rollback from {self.slot}.{self.block_hash}")
        stmt = (
            sqla.select(UTxO.created_slot, UTxO.block_hash)
            .distinct()  # otherwise we'd revert to 1 block >1 times
            .order_by(UTxO.created_slot.desc())
        )
        self.session = Session(_ENGINE)
        self.res = self.session.execute(stmt)
        self.res.fetchone()  # do away with current block

    def prev_block(self):
        row = self.res.fetchone()
        if (self.original_slot - self.slot) >= MAX_ALLOWED_ROLLBACK:
            raise Exception("Exceeded maximal rollback length - is the node synced?")
        if row is None:
            raise Exception("No more blocks to roll back!")

        self.slot, self.block_hash = row
        _LOGGER.warning(
            f"Rolled back {self.original_slot - self.slot} blocks, now at {self.slot}.{self.block_hash}"
        )
        return self.slot, self.block_hash

    def rollback(self):
        # TODO properly implement

        # delete everything newer than the block that we roll back to
        _LOGGER.warning(f"Executing rollback to block {self.slot}.{self.block_hash}")

        # Deleting UTxO will also delete placed orders, partial matches and pool states
        self.session.execute(sqla.delete(UTxO).where(UTxO.created_slot > self.slot))

        self.session.commit()
