import datetime
from typing import List

from common.classes import Asset, Token


def slot_timestamp(slot_no: int) -> int:
    # TODO: check https://github.com/CardanoSolutions/ogmios/issues/3
    return 1596491091 + (slot_no - 4924800)


def timestamp_slot(timestamp: int) -> int:
    return (timestamp - 1596491091) + 4924800


def slot_datestring(slot_no: int) -> int:
    return datetime.utcfromtimestamp(slot_timestamp(slot_no)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def parse_assets_to_list(value: dict) -> List[Asset]:
    return [
        Asset(
            int(amount),
            Token(
                policy_id if policy_id != "ada" else "",
                tokenname if tokenname != "lovelace" else "",
            ),
        )
        for policy_id, inner_dict in value.items()
        for tokenname, amount in inner_dict.items()
    ]
