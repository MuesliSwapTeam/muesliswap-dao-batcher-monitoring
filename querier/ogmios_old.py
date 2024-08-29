import json
import orjson
import logging

import websocket

from . import BlockIterator
from .config import OGMIOS_URL
from .rollback import RollbackHandler
import ipdb

_LOGGER = logging.getLogger(__name__)

TEMPLATE = {
    "jsonrpc": "2.0",
}

NEXT_BLOCK = TEMPLATE.copy()
NEXT_BLOCK["method"] = "nextBlock"
NEXT_BLOCK = orjson.dumps(NEXT_BLOCK)

QUERY_UTXOS_TEMPLATE = TEMPLATE.copy()
QUERY_UTXOS_TEMPLATE["method"] = "queryLedgerState/utxo"


class OgmiosIterator(BlockIterator):

    def __init__(self):
        self.utxo_info = {}

    def init_connection(self, start_slot, start_hash):
        self.ws = websocket.WebSocket()
        try:
            self.ws.connect(OGMIOS_URL)
        except OSError as ex:
            raise Exception(f"Can't connect to Ogmios server on {OGMIOS_URL}") from ex

        data = TEMPLATE.copy()
        data["method"] = "findIntersection"
        data["params"] = {"points": [{"slot": start_slot, "id": start_hash}]}

        _LOGGER.info(
            f"findIntersection, setting last block to: {start_slot}.{start_hash}"
        )
        self.ws.send(orjson.dumps(data))
        resp = orjson.loads(self.ws.recv())
        # Example in case of rollback: 01]: [2023-09-25 11:21:02,061] INFO     querier.ogmios {'IntersectionNotFound': {'tip': {'slot': 104074568, 'hash': '82>
        if "error" in resp.keys():
            # Rollback: We need to find the last common ancestor block (i believe this can't be more than the security parameter, so we can just iterate backwards until we find it)
            rollback_handler = RollbackHandler()
            while True:
                slot, block_hash = rollback_handler.prev_block()
                data["params"]["points"][0] = {"slot": slot, "id": block_hash}
                self.ws.send(orjson.dumps(data))
                resp = orjson.loads(self.ws.recv())
                if "error" in resp.keys():
                    rollback_handler.rollback()
                    break

        self.ws.send(NEXT_BLOCK)
        self.ws.recv()  # this just says roll back to the intersection (we already did)

    def iterate_blocks(self):
        # we want to always keep 100 blocks in queue to avoid waiting for node
        for i in range(100):
            self.ws.send(NEXT_BLOCK)
        while True:
            resp = self.ws.recv()
            # fast: check whether string is anywhere in tx
            if "backward" in resp:
                # slow: deserialize and check if value in correct field
                resp = orjson.loads(resp)
                if resp["result"]["direction"] == "backward":
                    # TODO change this logic. should be handled more gracefully
                    raise Exception(
                        "Ogmios Rollback!"
                    )  # this will restart querier and trigger rollback above
            # This handles responses to requests made by Querier for transaction input UTxOs
            if "queryLedgerState/utxo" in resp:
                resp = orjson.loads(resp)
                if resp["method"] == "queryLedgerState/utxo":
                    for utxo in resp["result"]:
                        self.utxo_info[
                            f"{utxo['transaction']['id']}#{utxo['transaction']['index']}"
                        ] = utxo
                    self.ws.send(NEXT_BLOCK)
                    continue
            self.ws.send(NEXT_BLOCK)
            yield resp
