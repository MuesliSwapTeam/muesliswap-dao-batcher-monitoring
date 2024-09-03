import requests
import pickle
from typing import List, Tuple
from sqlalchemy.orm import Session
import sqlalchemy
from cardano_python_utils.datums import datum_from_cborhex
from cardano_python_utils.classes import Token, LOVELACE, ShelleyAddress
import ipdb
from argparse import Namespace
from collections import defaultdict
import pycardano
import logging


from common.db import Batcher, BatcherAddress, Order, Transaction, UTxO
from common.util import parse_assets_to_list
from .config import (
    MUESLI_ADDR_TO_VERSION,
    PRICE_EP,
    BLOCKFROST,
    POOL_CONTRACTS,
    PROFIT_ADDRESSES,
)

_LOGGER = logging.getLogger(__name__)


# def get_prices():
#     try:

#         response = requests.get(PRICE_EP)
#         response.raise_for_status()  # Raise an exception for HTTP errors

#         # Check if the content type is the one expected for a pickle file
#         if "application/octet-stream" in response.headers.get("Content-Type", ""):
#             data = pickle.loads(response.content)  # Deserialize the pickle data
#         else:
#             print("Unexpected content type:", response.headers.get("Content-Type"))
#             return None

#         return data
#     except requests.exceptions.RequestException as e:
#         print(f"Error querying prices: {e}")
#         return None
#     except pickle.UnpicklingError as e:
#         print(f"Error unpickling data: {e}")
#         return None


def get_price_in_ada(token: Token):
    quote_policy_id = ""
    quote_name = ""
    base_policy_id = token.policy_id
    base_name = token.name

    # Base and quote are flipped because that is how the middleware expects it :(
    params = {
        "quote-policy-id": base_policy_id,
        "quote-tokenname": base_name,
        "base-policy-id": quote_policy_id,
        "base-tokenname": quote_name,
    }

    response = requests.get(PRICE_EP, params=params)
    return response.json()


def initialise_open_orders(engine: sqlalchemy.engine) -> dict:

    open_orders = dict()

    with Session(engine) as session:
        query = session.query(Order.id).filter(Order.transaction_id == None)
        for row in query.all():
            open_orders[row[0]] = True
    return open_orders


def parse_output(
    tx: dict,
    output: dict,
    id: str,
    slot: int,
    block_hash: str,
) -> UTxO:
    contract_version = MUESLI_ADDR_TO_VERSION.get(output["address"], None)
    if contract_version:
        # Muesliswap order
        sender, recipient = parse_datum(tx, output, contract_version)
        return Order(
            id=id,
            sender=sender,
            recipient=recipient,
            slot=slot,
        )
    else:
        # Generic UTxO. Stored in case it is a batcher's UTxO in a future transaction
        return UTxO(
            id=id,
            value=output["value"],
            owner=output["address"],
            created_slot=slot,
            block_hash=block_hash,
        )


def parse_datum(tx: dict, output: dict, contract_version: str):

    datum_hex = output.get("datum", None)
    datum_hash = output.get("datumHash", None)
    if datum_hex is not None:
        datum = datum_from_cborhex(datum_hex)
    elif datum_hash in tx["datums"]:
        datum = datum_from_cborhex(tx["datums"][datum_hash])
    else:
        # TODO handle muesli v1 reconstruct datum from metadata
        _LOGGER.error(
            f"No datum attached.\n"
            f"  Smart contract version: {contract_version}.\n"
            f"  Transaction: {tx['id']}"
        )
        raise Exception("No datum attached")

    if "lq" in contract_version:
        sender_pkh, sender_skh = parse_wallet_address(datum["fields"][0])
        recipient_pkh, recipient_skh = parse_wallet_address(datum["fields"][1])
        return sender_pkh + sender_skh, recipient_pkh + recipient_skh

    if contract_version in ["v2", "v3", "v4"]:
        datum = datum["fields"][0]["fields"]
        sender_pkh, sender_skh = parse_wallet_address(datum[0])
        sender = sender_pkh + sender_skh
        return sender, sender


def parse_bf_datum(utxo: Namespace, contract_version: str):
    if utxo.inline_datum:
        datum = datum_from_cborhex(utxo.inline_datum)
    else:
        datum = BLOCKFROST.script_datum_cbor(utxo.data_hash)
        datum = datum_from_cborhex(datum.cbor)

    if "lq" in contract_version:
        sender_pkh, sender_skh = parse_wallet_address(datum["fields"][0])
        recipient_pkh, recipient_skh = parse_wallet_address(datum["fields"][1])
        return sender_pkh + sender_skh, recipient_pkh + recipient_skh

    if contract_version in ["v2", "v3", "v4"]:
        datum = datum["fields"][0]["fields"]
        sender_skh, sender_pkh = parse_wallet_address(datum[0])
        sender = sender_pkh + sender_skh
        return sender, sender


def parse_wallet_address(datum: dict):
    pkh = datum["fields"][0]["fields"][0]["bytes"]
    skh_cons = datum["fields"][1]
    try:
        skh = skh_cons["fields"][0]["fields"][0]["fields"][0]["bytes"]
    except (KeyError, IndexError):
        assert skh_cons["constructor"] == 1
        skh = ""
    return (pkh, skh)


def address_hex_to_bech32(pkh: str = None, skh: str = None, full: str = None) -> str:
    if full:
        return ShelleyAddress(
            mainnet=True, pubkeyhash=full[:56], stakekeyhash=full[56:]
        ).bech32
    return ShelleyAddress(mainnet=True, pubkeyhash=pkh, stakekeyhash=skh).bech32


def parse_value_bf_to_ogmios(value: Namespace) -> dict:
    ret = {}
    for asset in value:
        token = Token.from_hex(asset.unit)
        ret[token.policy_id] = {token.name: asset.quantity}

    return ret


def filter_utxos(outputs):
    ret = []
    for o in outputs:
        if not isinstance(o, UTxO):
            continue
        if str(pycardano.Address.decode(o.owner).payment_part) in POOL_CONTRACTS:
            continue
        if o.owner in PROFIT_ADDRESSES:
            continue
        ret.append(o)

    return ret


def calculate_analytics(
    inputs: List[UTxO],
    outputs: List[UTxO],
    orders: List[Order],
    session: Session,
) -> Tuple[Batcher, dict, int, int]:
    """
    Returns the batcher, batcher's ADA revenue, a dictionary mapping non-ADA tokens to their revenue
    and a sum of the non-ADA amounts converted to ADA using the latest prices.
    """

    recipients = [
        ShelleyAddress(
            mainnet=True, pubkeyhash=o.recipient[:56], stakekeyhash=o.recipient[56:]
        ).bech32
        for o in orders
    ]
    senders = [
        ShelleyAddress(
            mainnet=True, pubkeyhash=o.sender[:56], stakekeyhash=o.sender[56:]
        ).bech32
        for o in orders
    ]

    in_assets = defaultdict(int)
    addresses = set()
    for input_utxo in inputs:
        if input_utxo.owner in senders:
            continue
        addresses.add(input_utxo.owner)
        assets = parse_assets_to_list(input_utxo.value)
        for asset in assets:
            in_assets[asset.token] += asset.amount

    addresses = list(addresses)

    if len(addresses) == 0:
        # Can happen for some cancellations
        batcher = None

    elif len(addresses) == 1:
        try:
            batcher = (
                session.query(Batcher)
                .join(BatcherAddress, Batcher.id == BatcherAddress.batcher_id)
                .filter(BatcherAddress.address == addresses[0])
            ).one_or_none()
            if not batcher:
                batcher = Batcher()
                addr = BatcherAddress(address=addresses[0], batcher=batcher)
                session.add(batcher)
                session.add(addr)

        except:
            raise Exception(
                f"Multiple batchers associated with address: {addresses[0]}"
            )
    else:
        ipdb.set_trace()
        batcher_list = []
        unassociated_addresses = []
        for address in addresses:
            try:
                batcher = (
                    session.query(Batcher)
                    .join(BatcherAddress, Batcher.id == BatcherAddress.batcher_id)
                    .filter(BatcherAddress.address == address)
                ).one_or_none()
                if batcher:
                    batcher_list.append(batcher)
                else:
                    unassociated_addresses.append(address)
            except:
                raise Exception(f"Multiple batchers associated with address: {address}")
        if len(batcher_list) == 0:
            batcher = Batcher()
            session.add(batcher)
        if len(batcher_list) > 1:
            for i in range(1, len(batcher_list)):
                if batcher_list[0].id != batcher_list[i].id:
                    for address in batcher_list[i].addresses:
                        address.batcher_id = batcher_list[0].id
                    for transaction in batcher_list[i].transactions:
                        transaction.batcher_id = batcher_list[0].id
                    session.delete(batcher_list[i])
            batcher = batcher_list[0]
        for unassociated_address in unassociated_addresses:
            addr = BatcherAddress(address=unassociated_address, batcher=batcher)
            session.add(addr)

    out_assets = defaultdict(int)
    for output_utxo in outputs:
        if (
            output_utxo.owner in recipients
            or output_utxo.owner in senders
            # or output_utxo.owner in MUESLI_POOL_ADDRESSES
        ):
            continue
        assets = parse_assets_to_list(output_utxo.value)
        for asset in assets:
            out_assets[asset.token] += asset.amount

    differences = defaultdict(int)
    for token, amount in out_assets.items():
        if token in in_assets:
            differences[token] = amount - in_assets[token]
        else:
            differences[token] = amount

    for token, amount in in_assets.items():
        if token not in out_assets:
            differences[token] = -amount

    ada_profit = 0
    equivalent_ada = 0
    zero_revenue_tokens = []
    for token, amount in differences.items():
        if amount == 0:
            zero_revenue_tokens.append(token)
            continue
        if token == LOVELACE:
            ada_profit += amount
        else:
            prices = get_price_in_ada(token)
            equivalent_ada += amount * prices["price"]
    for token in zero_revenue_tokens:
        del differences[token]

    if LOVELACE in differences:
        del differences[LOVELACE]

    differences = {k.to_hex(): v for k, v in differences.items()}

    if not batcher and len(addresses) > 0:
        ipdb.set_trace()

    return (batcher, ada_profit, differences, equivalent_ada)
