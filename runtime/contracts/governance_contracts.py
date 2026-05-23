from __future__ import annotations

from dataclasses import dataclass

GOVERNANCE_CONTRACT_VERSION = "33A"


@dataclass(frozen=True)
class GovernanceDecisionRef:
    contract_version: str
    decision: str
    reason: str
