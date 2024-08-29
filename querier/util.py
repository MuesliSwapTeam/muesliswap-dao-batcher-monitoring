import datetime
import common.db as db
from typing import List
from common.util import parse_assets_to_list


def initialise_open_orders() -> dict:

    open_orders = dict()
    query = """
    with last_partial_match as (
        select order_id, max(slot_no) as slot_no
        from "PartialMatch"
        group by order_id
    )
    SELECT
    COALESCE(pm_tx.hash, tx.hash),
    COALESCE(pm_tx.output_idx, tx.output_idx),
    o.dex_id
    FROM "Order" o
    JOIN "Tx" tx ON o.tx_id = tx.id
    LEFT OUTER JOIN last_partial_match lpm ON o.id = lpm.order_id
    LEFT OUTER JOIN "PartialMatch" pm ON lpm.slot_no = pm.slot_no
    LEFT OUTER JOIN "Tx" pm_tx ON pm.new_utxo_id = pm_tx.id
    WHERE o.full_match_id IS NULL AND o.cancellation_id IS NULL
    """
    with orm.Session(self.engine) as session:
        sql_query = sqlalchemy.text(query)
        result = session.execute(sql_query)
        for row in result:
            open_orders[f"{row[0]}#{row[1]}"] = row[2]

        # Get open liquidity orders
        query = session.query(db.Tx.hash, db.Tx.output_idx, db.LiquidityOrder.dex_id)
        query = query.join(db.LiquidityOrder, db.LiquidityOrder.tx_id == db.Tx.id)
        query = query.filter(db.LiquidityOrder.closed_slot_no == None)
        for row in query.all():
            open_orders[f"{row[0]}#{row[1]}"] = row[2]

    return open_orders


def parse_output(output: dict) -> db.UTxO:
    # TODO implement
    return db.UTxO(
        id=f"{output['transaction']['id']}#{output['index']}",
        tx_id=output["transaction"]["id"],
        index=output["index"],
        value=output["value"],
    )


def calculate_analytics(
    inputs: List[db.UTxO],
    outputs: List[db.UTxO],
    order_inputs: List[str],
    network_fee: int,
    prices=None,
):
    # TODO get fee
    recipients = []
    senders = []

    in_assets = {}
    for input_utxo in inputs:
        if f"{input_utxo.tx_id}#{input_utxo.index}" in order_inputs:
            continue
        assets = parse_assets_to_list(input_utxo.value)
        for asset in assets:
            in_assets[asset.token] = asset.amount

    out_assets = {}
    for output_utxo in outputs:
        if output.owner in recipients or output.owner in senders:
            continue
        assets = parse_assets_to_list(output_utxo.value)
        for asset in assets:
            out_assets[asset.token] = asset.amount

    differences = {}
    for token, amount in out_assets.items():
        if token in in_assets:
            differences[token] = amount - in_assets[token]
        else:
            differences[token] = amount

    for token, amount in in_assets.items():
        if token not in out_assets:
            differences[token] = -amount

    ada_revenue = 0
    for token, amount in differences.items():
        if token == "ada":
            ada_revenue += amount
        else:
            ada_revenue += amount * prices[("", token)]

    ada_profit = ada_revenue - network_fee
    return differences, ada_revenue, ada_profit
