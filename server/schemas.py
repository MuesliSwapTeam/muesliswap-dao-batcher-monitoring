from pydantic import BaseModel
from typing import List


class BatcherResponse(BaseModel):
    num_transactions: int
    addresses: List[str]


class BatcherStatsResponse(BaseModel):
    max_profit: float
    min_profit: float
    avg_profit: float
    total: float


class ExpandedBatcherStatsResponse(BatcherStatsResponse):
    num_transactions: int
    addresses: List[str]


class TransactionResponse(BaseModel):
    tx_hash: str
    ada_profit: int
    non_ada_profit: float
    other_assets: dict
