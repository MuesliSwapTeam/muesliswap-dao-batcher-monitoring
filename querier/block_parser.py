import sqlalchemy as sqla
from sqlalchemy import orm
import ogmios
from ogmios.datatypes import Block
import datetime
import logging

import util
from common.db import UTxO, Order, _ENGINE, Transaction


_LOGGER = logging.getLogger(__name__)
PRICE_UPDATE_INTERVAL = 180


class BlockParser:
    engine: sqla.Engine

    def __init__(self, block_iterator):
        self.iterator = block_iterator
        self.engine = _ENGINE
        self.current_slot = -1

        self.open_orders = util.initialise_open_orders(engine=self.engine)
        self.prices = util.get_prices()
        self.latest_price_update = datetime.datetime.now() if self.prices else -1

    def add_open_order(self, tx_id: str, contract_version: int):
        self.open_orders[tx_id] = contract_version

    def remove_open_order(self, tx_id: str):
        del self.open_orders[tx_id]

    def run(self):
        for block in self.iterator.iterate_blocks():
            with orm.Session(self.engine) as session:
                self.process_block(block, session)
                session.commit()

    def process_block(self, block: Block, session):
        self.current_slot = block.slot
        block_time = datetime.fromtimestamp(util.slot_timestamp(self.current_slot))
        _LOGGER.info(
            f"Processing block height: {self.current_slot} ({block_time.isoformat()})"
        )
        if block_time - self.latest_price_update > PRICE_UPDATE_INTERVAL:
            self.prices = util.get_prices()
            self.latest_price_update = block_time
            # TODO check if these times are in the same format

        for tx in block.transactions:
            # TODO add error handling here if necessary
            self.process_tx(tx, session)

    def process_tx(self, tx, session):
        order_inputs = []
        inputs = [
            f"{d['transaction']['id']}#{d['transaction']['index']}"
            for d in tx["inputs"]
        ]
        calculate_analytics = False
        for input_id in inputs:
            utxo = session.query(UTxO).filter_by(id=input_id).first()
            if utxo:
                utxo.spent_slot = self.current_slot

            if input_id in self.open_orders:
                # smart_contract_version = self.open_orders[input_utxo_id]
                # TODO: investigate muesli_orders logic
                # orders.add(input_utxo_id)
                calculate_analytics = True
                self.remove_open_order(input_id)
                order_inputs.append(input_id)
        if calculate_analytics:
            input_utxos = session.query(UTxO).filter(UTxO.id.in_(inputs)).all()
            if len(input_utxos) != len(inputs):
                # TODO check which are missing and get them from backup
                pass
            orders = session.query(Order).filter(Order.id.in_(order_inputs))
        output_utxos = [
            util.parse_output(output, f"{tx['id']}#{idx}", self.current_slot)
            for idx, output in enumerate(tx["outputs"])
        ]
        session.add_all(output_utxos)

        if calculate_analytics:
            analytics = util.calculate_analytics(
                inputs=inputs,
                outputs=[output for output in output_utxos if isinstance(output, UTxO)],
                orders=orders,
                prices=self.prices,
            )
            session.add(
                Transaction(
                    equivalent_ada=equivalent_ada,
                    net_assets=net_assets,
                    slot=self.current_slot,
                    network_fee=network_fee,
                    orders=orders,
                )
            )
            # TODO implement
