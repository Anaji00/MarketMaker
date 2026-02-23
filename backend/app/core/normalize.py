from __future__ import annotations

import json
from dataclasses import dataclass

@dataclass(frozen=True)
class NormalizedSignal:
    """
    Canonical Data Model.
    Regardless of whether data comes from Polymarket, SEC, or YFinance,
    it is converted into this standard structure before entering the system.
    """
    source: str
    symbol: str
    kind: str
    direction: str
    notional: float
    raw: dict


    def raw_json(self) -> str:
        return json.dumps(self.raw, default=str)