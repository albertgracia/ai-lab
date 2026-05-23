"""Federation contracts (bootstrap-only).

Contracts-first metadata for domain isolation. No operational logic.
"""

from __future__ import annotations

from dataclasses import dataclass


FEDERATION_CONTRACT_VERSION = "BOOTSTRAP-01"


@dataclass(frozen=True)
class DomainCallEnvelope:
    """Minimal envelope for cross-domain calls (future use).

    Kept intentionally small: this is metadata-only for now.
    """

    contract_version: str
    domain: str
    request_id: str
    evidence_scope: str = "unknown"
    utc_timestamp: float = 0.0
