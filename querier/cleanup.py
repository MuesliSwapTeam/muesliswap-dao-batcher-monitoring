from common.db import UTxO, _ENGINE
from common.util import timestamp_slot
import datetime


def remove_spent_utxos():
    """
    Removes UTxOs that have been spent for at least 24h from the database.
    This keeps the UTxO table relatively small while still allowing for rollbacks
    within the security window.
    """
    day_ago = datetime.datetime.now() - datetime.timedelta(days=1)
    oldest_slot = timestamp_slot(day_ago.timestamp())
    with orm.Session(_ENGINE) as session:
        spent_utxos = session.query(UTxO).filter(UTxO.spent_slot_no < oldest_slot).all()

        for utxo in spent_utxos:
            session.delete(utxo)

        session.commit()
