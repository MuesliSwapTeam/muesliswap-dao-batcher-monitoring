import ogmios
from ogmios.datatypes import TxOutputReference

if __name__ == "__main__":
    with ogmios.Client() as client:
        p, t, add = client.find_intersection.execute(
            [
                ogmios.datatypes.Point(
                    slot=125879282,
                    id="a783eb661f85f67fb11a5e003bd720a85ab02091a6137bc0ed883ce35eb2c3c6",
                )
            ]
        )
        direction, tip, block, _ = client.next_block.execute()
        # print(f"At height {tip.height}")
        direction, tip, block, _ = client.next_block.execute()
        print(f"At height {tip.height}")
        print(f"Block slot: {block.slot} Block hash: {block.id}")
        output_ref = TxOutputReference(
            tx_id="715b75c1fb64ed2ddb272a57f1d46aea2b7e0e6d40f360565a59fba7cf9e5807",
            index=0,
        )
        utxos = client.query_utxo.execute([output_ref])
        print(len(utxos))
        print(utxos)
