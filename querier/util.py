import datetime
import requests
import pickle
from common.db import Batcher, BatcherAddress, Order, Transaction, UTxO
from typing import List
from sqlalchemy.orm import Session
import sqlalchemy
from common.util import parse_assets_to_list
from .config import MUESLI_ADDR_TO_VERSION, PRICE_EP, MUESLI_POOL_ADDRESSES


def get_prices():
    try:

        response = requests.get(PRICE_EP)
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Check if the content type is the one expected for a pickle file
        if "application/octet-stream" in response.headers.get("Content-Type", ""):
            data = pickle.loads(response.content)  # Deserialize the pickle data
        else:
            print("Unexpected content type:", response.headers.get("Content-Type"))
            return None

        return data
    except requests.exceptions.RequestException as e:
        print(f"Error querying prices: {e}")
        return None
    except pickle.UnpicklingError as e:
        print(f"Error unpickling data: {e}")
        return None


def initialise_open_orders(engine: sqlalchemy.engine) -> dict:

    open_orders = dict()

    with Session(engine) as session:
        query = session.query(Order.id).filter(Order.transaction_id == None)
        for row in query.all():
            open_orders[f"{row[0]}#{row[1]}"] = row[2]
    return open_orders


def parse_output(output: dict, id: str, slot: int) -> UTxO:
    contract_version = MUESLI_ADDR_TO_VERSION.get(output["address"], None)
    if contract_version:
        # Muesliswap order
        sender, recipient = parse_datum(output["datum"], contract_version)
        return Order(
            id=id,
            sender=sender,
            recipient=recipient,
            slot=slot,
        )
    else:
        # Generic UTxO. Stored in case it is a batcher's UTxO in a future transaction
        return UTxO(
            id=id, value=output["value"], owner=output["address"], created_slot=slot
        )


def parse_datum(datum: dict, contract_version: str):

    if contract_version in ["v2", "v3", "v4"]:
        datum = datum["fields"][0]["fields"]
        creator = parse_wallet_address(datum[0])
        # buy_token = Token(datum[1]["bytes"], datum[2]["bytes"])
        # sell_token = Token(datum[3]["bytes"], datum[4]["bytes"])
        # buy_amount = int(datum[5]["int"])
        # allow_partial = datum[6]["constructor"] == 1
        # not actually used by SC, frontend only; someone even omits this
        # lovelace_attached = int(datum[7]["int"]) if len(datum) > 7 else 0
        return creator, creator


def parse_wallet_address(datum: dict):
    pkh = datum["fields"][0]["fields"][0]["bytes"]
    skh_cons = datum["fields"][1]
    try:
        skh = skh_cons["fields"][0]["fields"][0]["fields"][0]["bytes"]
    except (KeyError, IndexError):
        assert skh_cons["constructor"] == 1
        skh = ""
    return (pkh, skh)


def calculate_analytics(
    inputs: List[UTxO],
    outputs: List[UTxO],
    orders: List[Order],
    network_fee: int,
    session: Session,
    prices=None,
):
    # TODO get fee
    recipients = [o.recipient for o in orders]
    senders = [o.sender for o in orders]

    in_assets = {}
    addresses = []
    for input_utxo in inputs:
        if input_utxo.owner in MUESLI_POOL_ADDRESSES:
            continue
        addresses.append(input_utxo.owner)
        assets = parse_assets_to_list(input_utxo.value)
        for asset in assets:
            in_assets[asset.token] = asset.amount

    if len(addresses) == 1:
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

        if len(batcher_list) > 1:
            for i in range(1, len(batcher_list)):
                if batcher_list[0].id != batcher_list[i].id:
                    for address in batcher_list[i].addresses:
                        address.batcher_id = batcher_list[0].id
                    session.delete(batcher_list[i])

        batcher = batcher_list[0]
        for unassociated_address in unassociated_addresses:
            addr = BatcherAddress(address=unassociated_address, batcher=batcher)
            session.add(addr)

    out_assets = {}
    for output_utxo in outputs:
        if (
            output.owner in recipients
            or output.owner in senders
            or output.owner in MUESLI_POOL_ADDRESSES
        ):
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
