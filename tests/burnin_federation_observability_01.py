"""FEDERATION-OBSERVABILITY-01 burn-in.

Run:

  python3 tests/burnin_federation_observability_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_observability import (
    FederationPropagationTrace,
    get_federation_observability_snapshot,
    record_propagation_trace,
    reset_federation_observability_state,
)


def main() -> int:
    reset_federation_observability_state()

    # Simulate a few propagations.
    record_propagation_trace(
        FederationPropagationTrace(
            source_domain="gateway",
            target_domain="observability",
            authority_weight="high",
            budget_consumed={"chars": 120, "items": 6},
            overflow=False,
            truncated=False,
            degraded=False,
            rejected=False,
            path_depth=1,
        )
    )
    record_propagation_trace(
        FederationPropagationTrace(
            source_domain="gateway",
            target_domain="authority",
            authority_weight="high",
            budget_consumed={"chars": 1200, "items": 30},
            overflow=True,
            truncated=False,
            degraded=True,
            rejected=True,
            path_depth=1,
        )
    )

    snap = get_federation_observability_snapshot().to_dict()
    if snap["delegated_requests_total"] != 2:
        raise SystemExit("burnin_bad_total")
    if snap["rejected_domains_total"] != 1:
        raise SystemExit("burnin_bad_rejected")
    if snap["budget_overflows_total"] != 1:
        raise SystemExit("burnin_bad_overflows")

    print("OK burnin federation observability 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
