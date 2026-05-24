"""FEDERATION-COGNITIVE-GUARDS-01 tests (bounded cognition runtime protection)."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.federation_guards import (
    FederationPropagationCaps,
    get_federation_guard_events,
    get_federation_guard_runtime_state,
    get_federation_guard_summary,
    observe_federation_metadata_for_cognitive_guards,
    reset_federation_cognitive_guards_state,
)
from runtime.gateway.runtime_api_routes import handle_guard_routes


class _FakeHandler:
    def __init__(self, path: str):
        self.path = path
        self.sent = None

    def _send_json(self, code: int, payload: dict):
        self.sent = (code, payload)


def test_state_starts_normal_and_is_fail_safe():
    reset_federation_cognitive_guards_state()
    st = get_federation_guard_runtime_state(now=0.0)
    assert st["state"] == "NORMAL"
    summ = get_federation_guard_summary(now=0.0)
    assert summ["state"]["state"] == "NORMAL"


def test_lineage_depth_cap_emits_event_and_degrades_metadata():
    reset_federation_cognitive_guards_state()
    caps = FederationPropagationCaps(max_lineage_depth=1)
    out = observe_federation_metadata_for_cognitive_guards(
        {"_evidence_id": "abc", "_evidence_lineage_depth": 3, "_federation": {"authority_weight": "low"}, "_domain": "observability"},
        caps=caps,
        now=10.0,
    )
    assert out["_cognitive_guard"]["degraded"] is True
    assert "max_lineage_depth" in out["_cognitive_guard"]["caps_applied"]
    ev = get_federation_guard_events(limit=10)
    assert any(e["type"] == "lineage_depth_exceeded" for e in ev["events"])


def test_replay_amplification_transitions_to_constrained():
    reset_federation_cognitive_guards_state()
    caps = FederationPropagationCaps(max_evidence_reuse_rate=2, reuse_window_seconds=60, constrained_cooldown_seconds=60)
    meta = {"_evidence_id": "deadbeef" * 3, "_evidence_lineage_depth": 0, "_evidence_reuse_count": 0, "_federation": {"authority_weight": "low"}, "_domain": "observability"}
    observe_federation_metadata_for_cognitive_guards(meta, caps=caps, now=100.0)
    observe_federation_metadata_for_cognitive_guards(meta, caps=caps, now=101.0)
    observe_federation_metadata_for_cognitive_guards(meta, caps=caps, now=102.0)
    st = get_federation_guard_runtime_state(now=103.0)
    assert st["state"] in {"CONSTRAINED", "SAFE_MODE"}
    ev = get_federation_guard_events(limit=20)
    assert any(e["type"] == "replay_detected" for e in ev["events"])


def test_storm_detection_transitions_to_safe_mode():
    reset_federation_cognitive_guards_state()
    caps = FederationPropagationCaps(max_evidence_reuse_rate=999, reuse_window_seconds=60, event_window_seconds=60, safe_mode_cooldown_seconds=120)
    meta = {"_evidence_id": "storm", "_evidence_lineage_depth": 0, "_evidence_reuse_count": 0, "_federation": {"authority_weight": "low"}, "_domain": "observability"}
    for i in range(30):
        observe_federation_metadata_for_cognitive_guards(meta, caps=caps, now=200.0 + (i * 0.5))
    st = get_federation_guard_runtime_state(now=215.0)
    assert st["state"] == "SAFE_MODE"


def test_events_store_is_bounded_fifo():
    reset_federation_cognitive_guards_state()
    caps = FederationPropagationCaps(max_lineage_depth=0)
    for i in range(400):
        observe_federation_metadata_for_cognitive_guards({"_evidence_id": f"e{i}", "_evidence_lineage_depth": 1, "_domain": "observability", "_federation": {}}, caps=caps, now=300.0 + i)
    ev = get_federation_guard_events(limit=256)
    assert ev["events_total"] <= 256
    assert len(ev["events"]) <= 256


def test_guard_endpoints_are_fail_safe_and_compact():
    reset_federation_cognitive_guards_state()
    h = _FakeHandler("/runtime/guards/summary")
    assert handle_guard_routes(h) is True
    code, payload = h.sent
    assert code == 200
    assert payload["contract_version"] == "CG-01"
    assert "summary" in payload

    h2 = _FakeHandler("/runtime/guards/state")
    assert handle_guard_routes(h2) is True
    code, payload = h2.sent
    assert code == 200
    assert payload["state"]["state"] in {"NORMAL", "DEGRADED", "CONSTRAINED", "SAFE_MODE"}

    h3 = _FakeHandler("/runtime/guards/events?limit=3")
    assert handle_guard_routes(h3) is True
    code, payload = h3.sent
    assert code == 200
    assert payload["events"]["limit"] == 3
