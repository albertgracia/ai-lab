"""FEDERATION-CONTEXT-BUDGETS-01 burn-in.

Run:

  python3 tests/burnin_federation_context_budgets_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.context_budget import default_domain_limits, enforce_context_budget


def main() -> int:
    limits = default_domain_limits()

    # Authority: reject overflow.
    env = enforce_context_budget(domain="authority", payload={"blob": "x" * 10000}, limits=limits)
    if not env.rejected or not env.degraded:
        raise SystemExit("burnin_expected_authority_reject")

    # Observability: truncate overflow.
    env = enforce_context_budget(domain="observability", payload={"events": [str(i) for i in range(1000)]}, limits=limits)
    if not env.truncated or env.rejected:
        raise SystemExit("burnin_expected_observability_truncate")

    # Determinism.
    payload = {"a": "y" * 5000, "b": [str(i) for i in range(50)]}
    env1 = enforce_context_budget(domain="tests", payload=payload, limits=limits)
    env2 = enforce_context_budget(domain="tests", payload=payload, limits=limits)
    if env1.payload != env2.payload:
        raise SystemExit("burnin_nondeterministic_payload")

    print("OK burnin federation context budgets 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
