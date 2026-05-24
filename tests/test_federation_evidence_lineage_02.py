"""FEDERATION-EVIDENCE-LINEAGE-02 tests (runtime API handlers, bounded outputs)."""

from __future__ import annotations

import sys
import time

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_observability import reset_federation_observability_state, record_evidence_lineage
from runtime.gateway.runtime_api_routes import handle_evidence_routes


class _FakeHandler:
    def __init__(self, path: str):
        self.path = path
        self.sent = None

    def _send_json(self, code: int, payload: dict):
        self.sent = (code, payload)


def _seed_evidence(evidence_id: str = "deadbeef" * 3):
    record_evidence_lineage(
        evidence_summary={
            "schema_version": "EVID-01",
            "evidence_id": evidence_id,
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
            "propagation_count": 2,
            "reuse_count": 1,
            "replay_risk": {"level": "low", "replayed": True},
            "effective_confidence": 0.4,
            "degraded": True,
            "decay_reason": "replayed",
            "validation": "ok",
            "authority_bound": False,
        }
    )


def test_summary_endpoint_is_ok_and_bounded():
    reset_federation_observability_state()
    _seed_evidence()
    h = _FakeHandler("/runtime/evidence/summary")
    assert handle_evidence_routes(h) is True
    code, payload = h.sent
    assert code == 200
    assert payload["status"] in {"ok", "degraded"}
    assert "summary" in payload
    # Deterministic keys exist
    assert "evidence_propagations_total" in payload["summary"]


def test_hotspots_endpoint_respects_limit_param():
    reset_federation_observability_state()
    for i in range(20):
        _seed_evidence(evidence_id=("%024d" % i))
    h = _FakeHandler("/runtime/evidence/hotspots?limit=3")
    assert handle_evidence_routes(h) is True
    code, payload = h.sent
    assert code == 200
    hot = payload["hotspots"]
    assert hot["limit"] == 3


def test_lineage_endpoint_fail_safe_not_found():
    reset_federation_observability_state()
    h = _FakeHandler("/runtime/evidence/lineage/ffffffffffffffffffffffff")
    assert handle_evidence_routes(h) is True
    code, payload = h.sent
    assert code == 200
    assert payload["found"] is False


def test_lineage_endpoint_returns_seeded_evidence():
    reset_federation_observability_state()
    eid = "a" * 24
    _seed_evidence(evidence_id=eid)
    h = _FakeHandler(f"/runtime/evidence/lineage/{eid}")
    assert handle_evidence_routes(h) is True
    code, payload = h.sent
    assert code == 200
    assert payload["found"] is True
    assert payload["lineage"]["evidence_id"] == eid
