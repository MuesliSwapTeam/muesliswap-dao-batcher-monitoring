import datetime
import sqlalchemy.orm as orm

from common.db import UTxO, _ENGINE
from common.util import timestamp_slot


def remove_spent_utxos(latest_slot: int) -> int:
    """
    Removes UTxOs that have been spent for at least 24h from the database.
    This keeps the UTxO table relatively small while still allowing for rollbacks
    within the security window.
    """
    # day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    # oldest_slot = timestamp_slot(day_ago.timestamp())
    oldest_slot = latest_slot - 24 * 60 * 60
    with orm.Session(_ENGINE) as session:
        spent_utxos = session.query(UTxO).filter(UTxO.spent_slot < oldest_slot).all()

        for utxo in spent_utxos:
            session.delete(utxo)

        session.commit()
    return oldest_slot
