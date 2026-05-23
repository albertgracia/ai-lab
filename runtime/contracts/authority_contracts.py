from __future__ import annotations

from dataclasses import dataclass

AUTHORITY_CONTRACT_VERSION = "35C"


@dataclass(frozen=True)
class AuthoritySnapshot:
    contract_version: str
    freshness: str
    confidence: str
    gaps_total: int = 0
