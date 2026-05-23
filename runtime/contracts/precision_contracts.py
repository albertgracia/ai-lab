from __future__ import annotations

from dataclasses import dataclass

PRECISION_CONTRACT_VERSION = "36B"


@dataclass(frozen=True)
class PrecisionMarkers:
    contract_version: str
    operational_precision_score: float
    partial_state_total: int = 0
    authority_conflicts_total: int = 0
    stale_evidence_total: int = 0
