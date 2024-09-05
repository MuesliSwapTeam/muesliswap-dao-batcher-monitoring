from typing import NewType
from functools import lru_cache
import pycardano
import cbor2
import logging

HexAddr = NewType("HexAddr", str)
Bech32Addr = NewType("Bech32Addr", str)

CBor = NewType("CBor", bytes)
CBorHex = NewType("CBorHex", str)

Datum = NewType("Datum", dict)


_LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1000000)
def bech32_encode(hex_repr: HexAddr) -> Bech32Addr:
    try:
        address = pycardano.Address.from_primitive(bytes.fromhex(hex_repr))
        return Bech32Addr(address.encode())
    except AssertionError:
        return None


@lru_cache(maxsize=1000000)
def bech32_decode(bech32: Bech32Addr) -> HexAddr:
    address = pycardano.Address.decode(bech32)
    return HexAddr(address.to_primitive().hex())


def datum_from_cbortag(cbor):
    if isinstance(cbor, cbor2.CBORTag):
        if 121 <= cbor.tag <= 121 + 6:
            constructor = cbor.tag - 121
            fields = cbor.value
        elif 1280 <= cbor.tag <= 1280 + (127 - 7):
            constructor = cbor.tag - 1280 + 7
            fields = cbor.value
        elif cbor.tag == 102:
            constructor, fields = cbor.value
        else:
            raise ValueError(f"Invalid cbor with tag {cbor.tag}")
        fields = list(map(datum_from_cbortag, fields))
        return {
            "constructor": constructor,
            "fields": fields,
        }
    if isinstance(cbor, int):
        return {
            "int": cbor,
        }
    if isinstance(cbor, bytes):
        return {
            "bytes": cbor.hex(),
        }
    if isinstance(cbor, list):
        return {
            "list": list(map(datum_from_cbortag, cbor)),
        }
    if isinstance(cbor, dict):
        return {
            "map": list(
                map(
                    lambda kv: {
                        "k": datum_from_cbortag(kv[0]),
                        "v": datum_from_cbortag(kv[1]),
                    },
                    cbor.items(),
                )
            ),
        }


def datum_from_cbor(cbor: CBor) -> Datum:
    # first convert hex to CBORTag
    try:
        raw_datum = cbor2.loads(cbor)
    except Exception as e:
        _LOGGER.warning("Encountered unknown error when deserializing", exc_info=e)
        raise NotImplementedError("Encountered unknown error when deserializing")
    # converted datum
    datum = datum_from_cbortag(raw_datum)
    return Datum(datum)


def datum_from_cborhex(cbor: CBorHex) -> Datum:
    return datum_from_cbor(CBor(bytes.fromhex(cbor)))
