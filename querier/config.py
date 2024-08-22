import os

from cardano_python_utils.classes import Bech32Addr, ShelleyAddress


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

# DEFAULT_START_SLOT = 46536192
DEFAULT_START_SLOT = 125879182
# DEFAULT_START_SLOT = 91529071
# DEFAULT_START_HASH = "b5103d738e8b48f523e2f3c23d6eabfad8dd3dd68291744485b0f2b683be6849"
DEFAULT_START_HASH = "f6566cd85706932d8e60d02cdd882640ec358e73b0c8171d969045c1bb1199e1"


OGMIOS_URL = os.environ.get("OGMIOS_URL", "ws://localhost:1337")
