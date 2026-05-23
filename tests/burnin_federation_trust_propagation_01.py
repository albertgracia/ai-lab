"""FEDERATION-TRUST-PROPAGATION-01 burn-in.

Run:

  python3 tests/burnin_federation_trust_propagation_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.trust_propagation import TrustEvidence, TrustLineageNode, build_trust_envelope, propagate_trust


def main() -> int:
    env = build_trust_envelope(
        source_domain="gateway",
        target_domain="observability",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="routing", authority_backed=False, freshness_seconds=0)],
        lineage=[TrustLineageNode(domain="gateway", evidence_count=1)],
        ttl_seconds=120,
    )
    d = propagate_trust(env)
    if not (0.0 <= d.trust_score <= 1.0):
        raise SystemExit("burnin_bad_trust_score")

    # TTL expired => degraded
    env2 = build_trust_envelope(
        source_domain="gateway",
        target_domain="semantic",
        origin_domain="gateway",
        evidence=[TrustEvidence(evidence_type="routing", authority_backed=False, freshness_seconds=0)],
        lineage=[TrustLineageNode(domain="gateway", evidence_count=1)],
        ttl_seconds=0,
    )
    d2 = propagate_trust(env2)
    if not d2.degraded:
        raise SystemExit("burnin_expected_degraded")

    print("OK burnin federation trust propagation 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
