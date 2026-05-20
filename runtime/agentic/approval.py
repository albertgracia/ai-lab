"""FASE 28.0.6 — Approval Gate with HMAC tickets.

NO execution without a valid, signed approval ticket.
Tickets are single-use, time-limited, and verify plan integrity.

During FASE 28.0 simulation: tickets are generated but execution is always simulated.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_lib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


APPROVAL_SECRET: str = "ai-lab-agentic-approval-v1"
APPROVAL_TTL: dict[str, int] = {
    "workspace_write": 300,   # 5 min
    "runtime_write": 120,     # 2 min
    "privileged": 60,         # 1 min
    "none": 0,
}

USED_TICKETS: set[str] = set()


@dataclass
class ApprovalTicket:
    approval_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    plan_id: str = ""
    plan_hash: str = ""
    dry_run_hash: str = ""
    scope: str = "full"
    scope_actions: list[str] = field(default_factory=list)
    approval_type: str = ""
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    single_use: bool = True
    hmac_signature: str = ""
    simulation_only: bool = True

    def sign(self, secret: str = APPROVAL_SECRET) -> str:
        payload = f"{self.plan_hash}:{self.dry_run_hash}:{int(self.expires_at)}"
        self.hmac_signature = hmac_lib.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()[:32]
        return self.hmac_signature

    def verify(self, secret: str = APPROVAL_SECRET) -> bool:
        payload = f"{self.plan_hash}:{self.dry_run_hash}:{int(self.expires_at)}"
        expected = hmac_lib.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()[:32]
        return hmac_lib.compare_digest(self.hmac_signature, expected)

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return {
            "approval_id": self.approval_id,
            "plan_id": self.plan_id,
            "plan_hash": self.plan_hash,
            "scope": self.scope,
            "approval_type": self.approval_type,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "simulation_only": self.simulation_only,
        }


class ApprovalGate:
    """Governs approval workflow for agentic plans."""

    @staticmethod
    def request_approval(plan_hash: str, dry_run_hash: str, approval_type: str) -> ApprovalTicket:
        ttl = APPROVAL_TTL.get(approval_type, 300)
        ticket = ApprovalTicket(
            plan_hash=plan_hash,
            dry_run_hash=dry_run_hash,
            approval_type=approval_type,
            expires_at=time.time() + ttl,
        )
        ticket.sign()
        return ticket

    @staticmethod
    def validate_ticket(
        ticket_data: dict,
        current_plan_hash: str,
        current_dry_run_hash: str,
    ) -> tuple[bool, str]:
        """Validate an approval ticket. Returns (valid, reason)."""
        try:
            ticket = ApprovalTicket(
                approval_id=ticket_data.get("approval_id", ""),
                plan_hash=ticket_data.get("plan_hash", ""),
                dry_run_hash=ticket_data.get("dry_run_hash", ""),
                approval_type=ticket_data.get("approval_type", ""),
                expires_at=float(ticket_data.get("expires_at", 0)),
                hmac_signature=ticket_data.get("hmac_signature", ""),
            )

            # Check single-use
            if ticket.approval_id in USED_TICKETS:
                return False, "ticket_already_used"

            # Check expiration
            if ticket.is_expired():
                return False, "ticket_expired"

            # Check HMAC
            if not ticket.verify():
                return False, "hmac_invalid"

            # Check plan hash match
            if ticket.plan_hash != current_plan_hash:
                return False, "plan_hash_mismatch"

            # Check dry-run hash match
            if ticket.dry_run_hash != current_dry_run_hash:
                return False, "dry_run_hash_mismatch"

            # Mark as used
            USED_TICKETS.add(ticket.approval_id)
            return True, "valid"

        except Exception as e:
            return False, f"validation_error:{e}"

    @staticmethod
    def reject_ticket(ticket_data: dict) -> str:
        """Mark a ticket as rejected."""
        ticket_id = ticket_data.get("approval_id", "")
        USED_TICKETS.add(ticket_id)
        return ticket_id
