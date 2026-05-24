"""FEDERATION-EVIDENCE-LINEAGE-01 burn-in.

Run:

  python3 tests/burnin_federation_evidence_lineage_01.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.evidence_lineage import EvidenceOrigin, EvidenceSourceType, build_evidence_envelope


def main() -> int:
    origin = EvidenceOrigin(
        source_domain="gateway",
        source_role="gateway",
        model_profile="unknown",
        tool_name="",
        trust_scope="routing",
    )
    env1 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"q": "hello"},
        origin=origin,
        previous_seen_count=0,
        created_at=999.0,
    ).envelope
    env2 = build_evidence_envelope(
        evidence_type="routing_metadata",
        source_type=EvidenceSourceType.ROUTING,
        canonical_payload={"q": "hello"},
        origin=origin,
        previous_seen_count=1,
        created_at=111.0,
    ).envelope
    if env1.evidence_id != env2.evidence_id:
        raise SystemExit("burnin_non_deterministic_evidence_id")
    if env2.reuse.reuse_count < 1:
        raise SystemExit("burnin_expected_reuse")

    print("OK burnin federation evidence lineage 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
