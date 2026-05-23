from __future__ import annotations

from dataclasses import dataclass

FEDERATION_CONTRACT_VERSION = "BOOTSTRAP-01"


@dataclass(frozen=True)
class DomainBoundaryRule:
    contract_version: str
    src_domain: str
    dst_domain: str
    allowed: bool
    reason: str
