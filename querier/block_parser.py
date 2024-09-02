import sqlalchemy as sqla
from sqlalchemy import orm
import ogmios
from ogmios.datatypes import Block
import datetime
import logging
import ipdb

import querier.util as util
from common.db import UTxO, Order, _ENGINE, Transaction
from common.util import slot_timestamp
from .cleanup import remove_spent_utxos
from .config import BLOCKFROST, MUESLI_POOL_ADDRESSES


_LOGGER = logging.getLogger(__name__)
PRICE_UPDATE_INTERVAL = 180


class BlockParser:
    engine: sqla.Engine

    def __init__(self, iterator):
        self.iterator = iterator
        self.engine = _ENGINE
        self.current_slot = -1

        self.open_orders = util.initialise_open_orders(engine=self.engine)
        self.prices = util.get_prices()
        self.latest_price_update = datetime.datetime.now() if self.prices else -1

    def add_open_order(self, utxo_id: str):
        self.open_orders[utxo_id] = True

    def remove_open_order(self, tx_id: str):
        del self.open_orders[tx_id]

    def run(self):
        for i, block in enumerate(self.iterator.iterate_blocks()):
            with orm.Session(self.engine) as session:
                try:
                    self.process_block(block, session)
                except Exception as e:
                    ipdb.post_mortem()
                session.commit()
            if i % 1000 == 0:
                oldest_slot = remove_spent_utxos(self.current_slot)
                _LOGGER.info(f"Removed spent UTxOs up to slot {oldest_slot}")

    def process_block(self, block: Block, session):
        self.current_slot = block.slot
        block_time = datetime.datetime.fromtimestamp(slot_timestamp(self.current_slot))
        _LOGGER.info(
            f"Processing block height: {self.current_slot} ({block_time.isoformat()})"
        )
        if (
            datetime.datetime.now() - self.latest_price_update
        ).total_seconds() > PRICE_UPDATE_INTERVAL:
            self.prices = util.get_prices()
            self.latest_price_update = datetime.datetime.now()

        for tx in block.transactions:
            # TODO add error handling here if necessary
            self.process_tx(tx, block, session)

    def process_tx(self, tx, block, session):
        order_ids = []
        input_ids = [f"{d['transaction']['id']}#{d['index']}" for d in tx["inputs"]]
        calculate_analytics = False
        for input_id in input_ids:
            utxo = session.query(UTxO).filter_by(id=input_id).first()
            if utxo:
                utxo.spent_slot = self.current_slot
            if input_id in self.open_orders:
                # smart_contract_version = self.open_orders[input_utxo_id]
                # TODO: investigate muesli_orders logic
                # orders.add(input_utxo_id)
                calculate_analytics = True
                self.remove_open_order(input_id)
                order_ids.append(input_id)
        if calculate_analytics:
            input_utxos = session.query(UTxO).filter(UTxO.id.in_(input_ids)).all()
            # Number of cash UTxOs plus number of order UTxOs should equal total number of inputs
            if (len(input_utxos) + len(order_ids)) != len(input_ids):
                try:
                    utxos = BLOCKFROST.transaction_utxos(tx["id"])
                    stored_ids = [utxo.id for utxo in input_utxos]

                    for utxo in utxos.inputs:
                        input_id = f"{utxo.tx_hash}#{utxo.output_index}"
                        # fmt: off
                        if (
                            input_id not in stored_ids # Make sure we don't add duplicates
                            and input_id in input_ids # Make sure the input is actually in the transaction
                            and input_id not in order_ids # Make sure the input is not an order
                        ):
                        # fmt: on
                            input_utxos.append(
                                UTxO(
                                    id=input_id,
                                    value=util.parse_value_bf_to_ogmios(utxo.amount),
                                    owner=utxo.address,
                                    created_slot=self.current_slot,  # TODO
                                    block_hash="",  # TODO
                                )
                            )
                            # Blockfrost can return multiple instances of the same input,
                            # and also inputs that are not in the transaction (why?)
                            stored_ids.append(input_id)
                except Exception as e:
                    _LOGGER.error(f"Error fetching UTxOs: {e}")
                    return
            orders = session.query(Order).filter(Order.id.in_(order_ids)).all()
        output_utxos = [
            util.parse_output(
                tx=tx,
                output=output,
                id=f"{tx['id']}#{idx}",
                slot=self.current_slot,
                block_hash=block.id,
            )
            for idx, output in enumerate(tx["outputs"])
        ]

        for output_utxo in output_utxos:
            if isinstance(output_utxo, Order):
                self.add_open_order(output_utxo.id)
        session.add_all(output_utxos)

        if calculate_analytics:
            network_fee = tx["fee"]["ada"]["lovelace"]
            batcher, ada_revenue, net_assets, equivalent_ada = util.calculate_analytics(
                inputs=[i for i in input_utxos if i.owner not in MUESLI_POOL_ADDRESSES],
                outputs=[
                    output
                    for output in output_utxos
                    if (
                        isinstance(output, UTxO)
                        and output.owner not in MUESLI_POOL_ADDRESSES
                    )
                ],
                orders=orders,
                session=session,
                prices=self.prices,
            )
            session.add(
                Transaction(
                    batcher=batcher,
                    ada_revenue=ada_revenue,
                    network_fee=network_fee,
                    equivalent_ada=equivalent_ada,
                    net_assets=net_assets,
                    slot=self.current_slot,
                    orders=orders,
                    tx_hash=tx["id"],
                )
            )
