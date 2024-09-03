from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from common.db import Batcher, BatcherAddress, Transaction


def get_batchers(session: Session):
    # Query the Batcher with count of transactions and list of addresses
    batchers = (
        session.query(Batcher, func.count(Transaction.id).label("transaction_count"))
        .outerjoin(Batcher.transactions)  # Outer join with transactions
        .group_by(Batcher.id)  # Group by batcher id
        .options(joinedload(Batcher.addresses))  # Eager load addresses
        .all()
    )

    result = []
    for batcher, transaction_count in batchers:
        result.append(
            {
                "transaction_count": transaction_count,
                "addresses": [address.address for address in batcher.addresses],
            }
        )

    return result
