"""Federation contracts.

FEDERATION-ROLE-EXECUTION-01: contracts-first metadata for minimal role delegation.

Hard rules:
- Metadata only (no domain logic execution).
- No cross-domain mutation.
- No remediation/autofix intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


FEDERATION_CONTRACT_VERSION = "BOOTSTRAP-01"


class DelegationReason(str, Enum):
    KEYWORD_MATCH = "keyword_match"
    ROUTE_FAMILY_HINT = "route_family_hint"
    SAFETY_BLOCK = "safety_block"
    DEFAULT_CORE = "default_core"


class AuthorityWeight(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class ContextBudgetHint:
    """Guidance only. Enforced by caller/orchestrator."""

    max_chars: int = 1200
    max_items: int = 8
    reasoning_scope: str = "bounded"
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_chars": int(self.max_chars),
            "max_items": int(self.max_items),
            "reasoning_scope": self.reasoning_scope,
            "note": self.note,
        }


@dataclass(frozen=True)
class FederatedExecutionIntent:
    """Intent provided to the role router.

    This is a pure input contract for federation routing.
    """

    user_text: str
    route_family: str = "unknown"
    request_id: str = ""
    evidence_scope: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_text": self.user_text,
            "route_family": self.route_family,
            "request_id": self.request_id,
            "evidence_scope": self.evidence_scope,
        }


@dataclass(frozen=True)
class FederatedRoleDecision:
    """Role routing decision.

    Note: This does not execute anything. It only provides metadata.
    """

    contract_version: str
    domain: str
    role: str
    delegated_to: str
    reason: DelegationReason
    authority_weight: AuthorityWeight
    context_budget: ContextBudgetHint

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "domain": self.domain,
            "role": self.role,
            "delegated_to": self.delegated_to,
            "reason": self.reason.value,
            "authority_weight": self.authority_weight.value,
            "context_budget": self.context_budget.to_dict(),
        }


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "domain": self.domain,
            "request_id": self.request_id,
            "evidence_scope": self.evidence_scope,
            "utc_timestamp": float(self.utc_timestamp),
        }
