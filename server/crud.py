from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
import ipdb

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


def batcher_stats(session: Session, address: str):
    result = (
        session.query(
            func.max(Transaction.ada_profit + Transaction.equivalent_ada),
            func.min(Transaction.ada_profit + Transaction.equivalent_ada),
            func.avg(Transaction.ada_profit + Transaction.equivalent_ada),
            func.sum(Transaction.ada_profit + Transaction.equivalent_ada),
        )
        .join(Batcher, Batcher.id == Transaction.batcher_id)
        .join(BatcherAddress, BatcherAddress.batcher_id == Batcher.id)
        .filter(BatcherAddress.address == address)
    )

    max_profit, min_profit, avg_profit, total = result.first()

    if max_profit is None:
        return None

    return {
        "max_profit": max_profit,
        "min_profit": min_profit,
        "avg_profit": avg_profit,
        "total": total,
    }


def all_batcher_stats(session: Session):
    result = (
        session.query(
            func.max(Transaction.ada_profit + Transaction.equivalent_ada),
            func.min(Transaction.ada_profit + Transaction.equivalent_ada),
            func.avg(Transaction.ada_profit + Transaction.equivalent_ada),
            func.sum(Transaction.ada_profit + Transaction.equivalent_ada),
            func.count(Transaction.id),
            Batcher,
        )
        .join(Batcher, Batcher.id == Transaction.batcher_id)
        .options(joinedload(Batcher.addresses))
        .group_by(Batcher.id)
    )

    response = []
    for max_profit, min_profit, avg_profit, total, num_transactions, batcher in result:
        response.append(
            {
                "max_profit": max_profit,
                "min_profit": min_profit,
                "avg_profit": avg_profit,
                "total": total,
                "num_transactions": num_transactions,
                "addresses": [address.address for address in batcher.addresses],
            }
        )
    return response


# List of transactions per batcher
def batcher_transactions(session: Session, address: str):
    batcher = (
        session.query(Batcher)
        .options(joinedload(Batcher.transactions))  # Eager load transactions
        .filter(Batcher.addresses.any(address=address))
        .first()
    )

    result = []
    for transaction in batcher.transactions:
        result.append(
            {
                "tx_hash": transaction.tx_hash,
                "ada_profit": transaction.ada_profit,
                "non_ada_profit": transaction.equivalent_ada,
                "other_assets": transaction.net_assets,
            }
        )

    return result
