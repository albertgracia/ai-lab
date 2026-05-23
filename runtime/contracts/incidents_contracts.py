from __future__ import annotations

from dataclasses import dataclass

INCIDENTS_CONTRACT_VERSION = "36A"


@dataclass(frozen=True)
class IncidentSignal:
    contract_version: str
    incident_id: str
    severity: str
    primary_domain: str
