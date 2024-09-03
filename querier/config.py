import os
import blockfrost

from secret import BLOCKFROST_PROJECT_ID


MUESLISWAP_POOLS_API_URL = "https://api.muesliswap.com/liquidity/pools"

MUESLISWAP_V1_ORDERBOOK = "addr1wy2mjh76em44qurn5x73nzqrxua7ataasftql0u2h6g88lc3gtgpz"
MUESLISWAP_V2_ORDERBOOK = "addr1z8c7eyxnxgy80qs5ehrl4yy93tzkyqjnmx0cfsgrxkfge27q47h8tv3jp07j8yneaxj7qc63zyzqhl933xsglcsgtqcqxzc2je"
MUESLISWAP_V3_ORDERBOOK = "addr1z8l28a6jsx4870ulrfygqvqqdnkdjc5sa8f70ys6dvgvjqc3r6dxnzml343sx8jweqn4vn3fz2kj8kgu9czghx0jrsyqxyrhvq"
MUESLISWAP_V4_ORDERBOOK = "addr1zyq0kyrml023kwjk8zr86d5gaxrt5w8lxnah8r6m6s4jp4g3r6dxnzml343sx8jweqn4vn3fz2kj8kgu9czghx0jrsyqqktyhv"


MUESLISWAP_V1_LIQUIDITY = "addr1wydncknydgqcur8m6s8m49633j8f2hjcd8c2l48cc45yj0s4ta38n"
MUESLISWAP_V2_LIQUIDITY = "addr1w9e7m6yn74r7m0f9mf548ldr8j4v6q05gprey2lhch8tj5gsvyte9"
MUESLISWAP_CLP_LIQUIDITY = "addr1w87gl00kfuj7qnk8spf25x5e0wfcvasgj5tq3lt5egh6swc4aa5lh"

MUESLI_ADDR_TO_VERSION = {
    MUESLISWAP_V1_ORDERBOOK: "v1",
    MUESLISWAP_V2_ORDERBOOK: "v2",
    MUESLISWAP_V3_ORDERBOOK: "v3",
    MUESLISWAP_V4_ORDERBOOK: "v4",
    MUESLISWAP_V1_LIQUIDITY: "v1_lq",
    MUESLISWAP_V2_LIQUIDITY: "v2_lq",
    MUESLISWAP_CLP_LIQUIDITY: "clp_lq",
}

POOL_CONTRACTS = [
    "e8baad9288dc9abdc099b46f2ac006b1a82c7df4996e067f00c04e8d",  # v1
    "7045237d1eb0199c84dffe58fe6df7dc5d255eb4d418e4146d5721f8",  # v2
    "4136eeede1a49030451ee3a09d900959bafeafd9b536e59345ac780f",  # clp
    "28bbd1f7aebb3bc59e13597f333aeefb8f5ab78eda962de1d605b388",  # teddy
    "e628bfd68c07a7a38fcd7d8df650812a9dfdbee54b1ed4c25c87ffbf",  # spectrum v1
    "6b9c456aa650cb808a9ab54326e039d5235ed69f069c9664a8fe5b69",  # spectrum v2
    "32a3548883f31e79c13b5403ab92d3d0c4e54e9230a3d72cb1fb4c24",  # Cerra AMM Batcher (?)
]
# eg. Cerra transaction e0ba2dbd539384dba752a14d3e158c844f9b8d4078ba04860be026979a781a4b

PROFIT_ADDRESSES = [
    "addr1qycewgm43uc96vt3qjp434mqp4jfzttws0xjwqz4a364qu95mx98r9d2mpx5ka4xe5npakhrz2qz4n2tqzgvyngrkedqn3hctc",  # MuesliSwap
    "addr1q8l7hny7x96fadvq8cukyqkcfca5xmkrvfrrkt7hp76v3qvssm7fz9ajmtd58ksljgkyvqu6gl23hlcfgv7um5v0rn8qtnzlfk",  # MuesliSwap
    "addr1q9ry6jfdgm0lcrtfpgwrgxg7qfahv80jlghhrthy6w8hmyjuw9ngccy937pm7yw0jjnxasm7hzxjrf8rzkqcj26788lqws5fke",  # VyFi
]

MUESLI_ORDER_CONTRACTS = [
    MUESLISWAP_V1_ORDERBOOK,
    MUESLISWAP_V2_ORDERBOOK,
    MUESLISWAP_V3_ORDERBOOK,
    MUESLISWAP_V4_ORDERBOOK,
    MUESLISWAP_V1_LIQUIDITY,
    MUESLISWAP_V2_LIQUIDITY,
    MUESLISWAP_CLP_LIQUIDITY,
]

# DEFAULT_START_SLOT = 46536192
# DEFAULT_START_HASH = "b5103d738e8b48f523e2f3c23d6eabfad8dd3dd68291744485b0f2b683be6849"

# DEFAULT_START_SLOT = 125879182
# DEFAULT_START_HASH = "f6566cd85706932d8e60d02cdd882640ec358e73b0c8171d969045c1bb1199e1"

DEFAULT_START_SLOT = 133706202
DEFAULT_START_HASH = "770685fbaa53286ced25d46d6e1756eca23a143b493e194577fee1870aeda5cc"

OGMIOS_URL = os.environ.get("OGMIOS_URL", "ws://localhost:1337")
# PRICE_EP = "https://aggregator-analytics.muesliswap.com/v2/all-prices"
PRICE_EP = "https://api.muesliswap.com/price"
BLOCKFROST = blockfrost.BlockFrostApi(
    BLOCKFROST_PROJECT_ID, base_url="https://cardano-mainnet.blockfrost.io/api"
)
