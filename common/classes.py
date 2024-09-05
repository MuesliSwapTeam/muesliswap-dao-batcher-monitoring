from dataclasses import dataclass
from typing import NewType
from .cardano_utils import bech32_encode, bech32_decode, Bech32Addr, HexAddr

PolicyId = NewType("PolicyId", str)
HexTokenName = NewType("HexTokenName", str)

PubKeyHash = NewType("PubKeyHash", str)
StakeKeyHash = NewType("StakeKeyHash", str)


@dataclass(frozen=True)
class Token:
    """Represents a token.

    Fields:
    policy_id -- policy id associated with the asset/token type
    name      -- name of the asset under its policy id in hex
    """

    policy_id: PolicyId
    name: HexTokenName

    def __str__(self):
        """
        Human readable version
        """
        if self.name == "":
            if self.policy_id == "":
                return "lovelace"
            return self.policy_id
        try:
            return f"{self.policy_id}.{bytes.fromhex(self.name).decode('utf8')}"
        except UnicodeDecodeError:
            return f"{self.policy_id}.{self.name}"

    def to_hex(self):
        """
        Version sent to the outside
        """
        return f"{self.policy_id}.{self.name}"

    def to_cardano_cli(self):
        """
        Version required by cardano-node since 1.33.0
        """
        if not self.name:
            if not self.policy_id:
                return "lovelace"
            return self.policy_id
        return f"{self.policy_id}.{self.name}"

    @classmethod
    def from_string(cls, s: str):
        first_dot = s.find(".")
        spl = s[:first_dot], s[first_dot + 1 :]
        if len(spl) == 1:
            if spl[1] == "lovelace":
                return cls(PolicyId(""), HexTokenName(""))
            else:
                return cls(PolicyId(spl[0]), HexTokenName(""))
        if len(spl) == 2:
            return cls(PolicyId(spl[0]), HexTokenName(spl[1].encode("utf8").hex()))
        raise RuntimeError("Invalid token string")

    @classmethod
    def from_hex(cls, s: str):
        if len(s) > 56:
            swodot = s.replace(".", "")
            spl = swodot[:56], swodot[56:]
            return cls(PolicyId(spl[0]), HexTokenName(spl[1]))
        else:
            if s == "lovelace" or s == "" or s == ".":
                return cls(PolicyId(""), HexTokenName(""))
            elif len(s) == 56:
                return cls(PolicyId(s), HexTokenName(""))
        raise RuntimeError("Invalid token string")

    def __hash__(self):
        return hash((self.name, self.policy_id))

    def __lt__(self, other):
        assert isinstance(other, Token)
        return self.policy_id < other.policy_id or (
            self.policy_id == other.policy_id and self.name < other.name
        )

    @property
    def subject(self):
        return f"{self.policy_id}{self.name}"

    def __eq__(self, o):
        try:
            return self.name == o.name and self.policy_id == o.policy_id
        except AttributeError:
            return False


LOVELACE = Token(PolicyId(""), HexTokenName(""))


@dataclass(frozen=True)
class Asset:
    amount: int
    token: Token

    def __hash__(self):
        return hash((self.amount, self.token))

    def serialize(self):
        return {
            "amount": str(self.amount),
            "token": self.token.to_hex(),
        }

    def __str__(self):
        return f"{self.amount} {self.token}"

    def __repr__(self):
        return f"Asset({self.amount}, {self.token})"


@dataclass(frozen=True)
class ShelleyAddress:
    mainnet: bool
    pubkeyhash: PubKeyHash
    stakekeyhash: StakeKeyHash = ""

    @property
    def network_tag(self):
        return "1" if self.mainnet else "0"

    @property
    def header(self):
        return "0" if self.stakekeyhash else "6"

    @property
    def hex(self) -> HexAddr:
        return HexAddr(
            f"{self.header}{self.network_tag}{self.pubkeyhash}{self.stakekeyhash}"
        )

    @property
    def bech32(self) -> Bech32Addr:
        return bech32_encode(self.hex)

    @property
    def is_enterprise(self) -> bool:
        return not bool(self.stakekeyhash)

    @classmethod
    def from_hex(cls, hex_addr: HexAddr):
        if hex_addr.startswith("0x"):
            hex_addr = hex_addr[2:]
        mainnet = hex_addr[1] == "1"
        pkh = PubKeyHash(hex_addr[2:58])
        if hex_addr[0] == "6" or hex_addr[0] == "7":
            return ShelleyAddress(pubkeyhash=pkh, mainnet=mainnet)
        elif hex_addr[0] == "0":
            return ShelleyAddress(
                pubkeyhash=pkh, mainnet=mainnet, stakekeyhash=hex_addr[58:]
            )
        else:
            raise NotImplementedError("Address type not implemented yet")

    @classmethod
    def from_bech32(cls, b_addr: Bech32Addr):
        return cls.from_hex(bech32_decode(b_addr))

    def __str__(self):
        return str(self.bech32)

    def __repr__(self):
        return f"ShelleyAddress({self.bech32})"
