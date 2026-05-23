"""FEDERATION-ROLE-EXECUTION-01 burn-in.

Lightweight deterministic burn-in to ensure role routing stays bounded and safe.
Run manually:

  python3 tests/burnin_federation_role_execution_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.contracts import FederatedExecutionIntent
from runtime.federation.role_router import resolve_role


SAMPLES: list[tuple[str, str]] = [
    ("prometheus targets down", "observability"),
    ("operational truth freshness gaps", "authority"),
    ("discoverable-only vs operational stale", "semantic"),
    ("RCA del incidente P1", "incidents"),
    ("time semantics NTP timezone", "infrastructure"),
    ("systemctl restart ailab-gateway", "operator_intent"),
    ("runbook gitnexus index rebuild", "docs"),
]


def main() -> int:
    for text, expected in SAMPLES:
        decision = resolve_role(FederatedExecutionIntent(user_text=text, route_family="unknown"))
        if decision.domain != expected:
            raise SystemExit(f"burnin_mismatch: text={text!r} expected={expected} got={decision.domain}")
        if decision.delegated_to == "remediation":
            raise SystemExit(f"burnin_forbidden_remediation: text={text!r}")
    print(f"OK burnin federation role execution 01 samples={len(SAMPLES)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
