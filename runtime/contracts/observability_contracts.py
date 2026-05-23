from __future__ import annotations

from dataclasses import dataclass

OBSERVABILITY_CONTRACT_VERSION = "30I-D"


@dataclass(frozen=True)
class SensorFusionSnapshotRef:
    contract_version: str
    utc_timestamp: float
    missing_sources_count: int = 0
