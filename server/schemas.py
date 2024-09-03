from pydantic import BaseModel
from typing import List


class BatcherStats(BaseModel):
    num_transactions: int
    addresses: List[str]
