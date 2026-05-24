"""FEDERATION-EVIDENCE-LINEAGE-02 burn-in.

Run:

  python3 tests/burnin_federation_evidence_lineage_02.py
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_observability import reset_federation_observability_state, record_evidence_lineage
from runtime.gateway.runtime_api_routes import handle_evidence_routes


class _FakeHandler:
    def __init__(self, path: str):
        self.path = path
        self.sent = None

    def _send_json(self, code: int, payload: dict):
        self.sent = (code, payload)


def main() -> int:
    reset_federation_observability_state()
    eid = "b" * 24
    record_evidence_lineage(
        evidence_summary={
            "schema_version": "EVID-01",
            "evidence_id": eid,
            "evidence_hash": "h" * 64,
            "evidence_type": "routing_metadata",
            "source_domain": "observability",
            "source_type": "observability",
            "authority_binding": {"authority_bound": False, "authority_domain": "", "binding_reason": ""},
            "created_at": 0.0,
            "canonical_payload_hash": "p" * 64,
            "freshness": {"freshness_ttl": 120, "freshness_seconds": 0, "state": "fresh"},
            "lineage_depth": 1,
            "ancestry_chain": ["parent"],
            "propagation_count": 1,
            "reuse_count": 0,
            "replay_risk": {"level": "none", "replayed": False},
            "effective_confidence": 0.4,
            "degraded": False,
            "decay_reason": "ok",
            "validation": "ok",
            "authority_bound": False,
        }
    )

    h = _FakeHandler("/runtime/evidence/summary")
    if not handle_evidence_routes(h):
        raise SystemExit("burnin_summary_not_handled")
    if h.sent[0] != 200:
        raise SystemExit("burnin_bad_code")

    h2 = _FakeHandler(f"/runtime/evidence/lineage/{eid}")
    handle_evidence_routes(h2)
    if not h2.sent[1].get("found"):
        raise SystemExit("burnin_expected_found")

    print("OK burnin federation evidence lineage 02")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
