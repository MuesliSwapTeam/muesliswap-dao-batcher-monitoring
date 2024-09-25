import ogmios
from ogmios.datatypes import Point
from .rollback import RollbackHandler
from . import OGMIOS_HOSTNAME

num_blocks_to_queue = 100


class OgmiosIterator:
    def __init__(self):
        pass

    def _init_connection(self, client: ogmios.Client, start_slot_no, start_block_hash):
        try:
            point, _, _ = client.find_intersection.execute(
                [Point(slot=start_slot_no, id=start_block_hash)]
            )
        except Exception as e:
            rollback_handler = RollbackHandler()
            while True:
                slot, block_hash = rollback_handler.prev_block()
                try:
                    point, _, _ = client.find_intersection.execute(
                        [Point(slot=slot, id=block_hash)]
                    )
                    rollback_handler.rollback()
                    break
                except:
                    pass
        finally:
            client.next_block.send()
            client.next_block.receive()

    def iterate_blocks(self, start_slot_no, start_block_hash):

        with ogmios.Client(host=OGMIOS_HOSTNAME) as client:
            # Ensures that the client points to the latest block in our database
            self._init_connection(client, start_slot_no, start_block_hash)
            for i in range(num_blocks_to_queue):
                client.next_block.send()
            while True:
                direction, tip, block, _ = client.next_block.receive()
                if direction == ogmios.Direction.backward:
                    raise Exception("Ogmios Rollback!")
                client.next_block.send()
                yield block


if __name__ == "__main__":
    import common.db as db
    import querier.config as config
    import ipdb

    start_slot_no, start_block_hash = db.get_max_slot_block_and_index()
    if start_slot_no > 0:
        rollback_handler = RollbackHandler()
        rollback_handler.prev_block()
        rollback_handler.rollback()

    # Now we find out what's the actual block that we should process first
    start_slot_no, start_block_hash = db.get_max_slot_block_and_index()
    if start_slot_no == 0 or not start_block_hash:
        start_slot_no = config.DEFAULT_START_SLOT
        start_block_hash = config.DEFAULT_START_HASH

    iterator = OgmiosIterator()
    block_generator = iterator.iterate_blocks(start_slot_no, start_block_hash)
    for block in block_generator:
        print(block)
        ipdb.set_trace()
