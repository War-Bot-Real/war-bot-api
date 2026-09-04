from dataclasses import dataclass
from typing import Literal

@dataclass
class Operation:
    type: Literal["add", "set"]
    value: int | float
    key: str | None = None