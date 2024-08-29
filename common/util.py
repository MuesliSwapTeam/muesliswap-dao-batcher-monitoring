import datetime
from cardano_python_utils.classes import Asset, Token
from typing import List


def slot_timestamp(slot_no: int) -> int:
    # TODO: check https://github.com/CardanoSolutions/ogmios/issues/3
    return 1596491091 + (slot_no - 4924800)


def timestamp_slot(timestamp: int) -> int:
    return (timestamp - 1596491091) + 4924800


def slot_datestring(slot_no: int) -> int:
    return datetime.utcfromtimestamp(slot_timestamp(slot_no)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def parse_assets_to_list(txo: dict) -> List[Asset]:
    assets_without_ada = {k: v for k, v in txo["value"].items() if k != "ada"}
    return [
        Asset(value, Token(policy_id, tokenname))
        for policy_id, inner_dict in assets_without_ada.items()
        for tokenname, value in inner_dict.items()
    ]
