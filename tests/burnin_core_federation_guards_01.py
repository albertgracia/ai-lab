"""CORE-HARDENING-FEDERATION-GUARDS-01 burn-in.

Run:

  python3 tests/burnin_core_federation_guards_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.contracts import FederatedExecutionIntent
from runtime.federation.role_router import build_routing_metadata


def main() -> int:
    # Normal case
    meta = build_routing_metadata(FederatedExecutionIntent(user_text="prometheus metrics", route_family="observe", request_id="r1"))
    if meta.get("_guard_status") not in {"ok", "degraded"}:
        raise SystemExit("burnin_guard_missing")
    if "_guard_violations" not in meta:
        raise SystemExit("burnin_guard_violations_missing")

    # Malformed injection simulation: missing budget keys should degrade.
    bad = {
        "_federation": {"domain": "observability", "delegated_to": "observability", "authority_weight": "medium"},
        "_domain": "observability",
        "_delegated_to": "observability",
    }
    from runtime.federation.federation_guards import validate_federation_metadata

    res = validate_federation_metadata(bad)
    if not res.degraded:
        raise SystemExit("burnin_expected_degraded")

    print("OK burnin core federation guards 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
