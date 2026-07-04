import os
import json
import time

import pytest

from runtime.hermes.loader import load_all, load_governance_modes, load_governance_matrix
from runtime.hermes.validation import validate_all
from runtime.hermes.status import build_status_report
from runtime.hermes.governance.resolver import GovernanceResolver, TriggerSignals


HERMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "hermes")


class TestGovernanceModesFile:
    def test_modes_json_exists(self):
        path = os.path.join(HERMES_DIR, "governance", "modes.json")
        assert os.path.exists(path)

    def test_modes_json_valid_json(self):
        path = os.path.join(HERMES_DIR, "governance", "modes.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "version" in data
        assert "modes" in data

    def test_all_four_modes_present(self):
        modes = load_governance_modes()
        expected = {"NORMAL", "ELEVATED", "DEGRADED", "LOCKDOWN"}
        assert set(modes.keys()) == expected

    def test_each_mode_has_required_fields(self):
        modes = load_governance_modes()
        for name, m in modes.items():
            assert m.description
            assert isinstance(m.allows, list) and len(m.allows) > 0
            assert isinstance(m.blocks, list) and len(m.blocks) > 0
            assert m.default_capability_behavior in (
                "read_only", "requires_approval", "blocked_except_observe", "blocked"
            )


class TestGovernanceMatrixFile:
    def test_matrix_json_exists(self):
        path = os.path.join(HERMES_DIR, "governance", "matrix.json")
        assert os.path.exists(path)

    def test_matrix_has_version(self):
        path = os.path.join(HERMES_DIR, "governance", "matrix.json")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert "version" in data
        assert "capability_governance" in data

    def test_all_capabilities_in_matrix(self):
        registry = load_all()
        cap_ids = {c.id for c in registry.capabilities}
        matrix = load_governance_matrix()
        for cid in cap_ids:
            assert cid in matrix, f"Capability '{cid}' missing from governance matrix"
        for cid in matrix:
            assert cid in cap_ids, f"Matrix has unknown capability '{cid}'"

    def test_each_cap_has_all_four_modes(self):
        matrix = load_governance_matrix()
        for cap_id, modes in matrix.items():
            for mode in ("NORMAL", "ELEVATED", "DEGRADED", "LOCKDOWN"):
                assert mode in modes, f"Capability '{cap_id}' missing mode '{mode}'"

    def test_all_statuses_valid(self):
        matrix = load_governance_matrix()
        valid = {"allowed", "requires_approval", "blocked"}
        for cap_id, modes in matrix.items():
            for mode_name, status in modes.items():
                assert status in valid, f"'{cap_id}/{mode_name}' has invalid status '{status}'"


class TestGovernanceResolver:
    def test_create_resolver(self):
        gr = GovernanceResolver()
        assert gr is not None

    def test_resolve_normal_by_default(self):
        gr = GovernanceResolver()
        signals = TriggerSignals()
        state = gr.resolve(signals)
        assert state.mode == "NORMAL"
        assert state.source == "control_plane"
        assert state.transition_count == 0

    def test_resolve_elevated_when_slo_red(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(slo_state="RED")
        state = gr.resolve(signals)
        assert state.mode == "ELEVATED"

    def test_resolve_elevated_when_light_degradation(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(degradation_level="LIGHT")
        state = gr.resolve(signals)
        assert state.mode == "ELEVATED"

    def test_resolve_degraded_when_heavy(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(degradation_level="HEAVY")
        state = gr.resolve(signals)
        assert state.mode == "DEGRADED"

    def test_resolve_degraded_when_emergency_degradation(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(degradation_level="EMERGENCY")
        state = gr.resolve(signals)
        assert state.mode == "DEGRADED"

    def test_resolve_lockdown_when_emergency_mode(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(emergency_mode=True)
        state = gr.resolve(signals)
        assert state.mode == "LOCKDOWN"

    def test_lockdown_overrides_degradation(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(emergency_mode=True, degradation_level="HEAVY")
        state = gr.resolve(signals)
        assert state.mode == "LOCKDOWN"

    def test_degraded_lower_priority_than_lockdown(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(emergency_mode=True, slo_state="GREEN")
        state = gr.resolve(signals)
        assert state.mode == "LOCKDOWN"

    def test_elevated_when_vram_high(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(vram_pressure=0.95)
        state = gr.resolve(signals)
        assert state.mode == "ELEVATED"

    def test_elevated_when_gpu_high(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(gpu_pressure=0.95)
        state = gr.resolve(signals)
        assert state.mode == "ELEVATED"

    def test_elevated_when_timeout_high(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(timeout_rate=0.15)
        state = gr.resolve(signals)
        assert state.mode == "ELEVATED"

    def test_normal_when_no_triggers(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(
            slo_state="GREEN", degradation_level="NONE",
            vram_pressure=0.5, gpu_pressure=0.6, timeout_rate=0.02,
        )
        state = gr.resolve(signals)
        assert state.mode == "NORMAL"

    def test_vram_normal_does_not_elevate(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(vram_pressure=0.8)
        state = gr.resolve(signals)
        assert state.mode == "NORMAL"

    def test_timeout_normal_does_not_elevate(self):
        gr = GovernanceResolver()
        signals = TriggerSignals(timeout_rate=0.05)
        state = gr.resolve(signals)
        assert state.mode == "NORMAL"

    def test_get_mode_description(self):
        gr = GovernanceResolver()
        desc = gr.get_mode_description("NORMAL")
        assert desc is not None
        assert "allows" in desc
        assert "blocks" in desc
        assert "requires_approval" in desc
        assert len(desc["allows"]) > 0
        assert len(desc["blocks"]) > 0

    def test_get_mode_description_locked(self):
        gr = GovernanceResolver()
        desc = gr.get_mode_description("LOCKDOWN")
        assert desc is not None
        assert "Active incident reporting" in desc["allows"]

    def test_get_modes_returns_all_four(self):
        gr = GovernanceResolver()
        modes = gr.get_modes()
        assert len(modes) == 4

    def test_get_matrix_returns_dict(self):
        gr = GovernanceResolver()
        matrix = gr.get_matrix()
        assert len(matrix) >= 6


class TestGovernanceCapabilityStatus:
    def test_ai_lab_runtime_allowed_in_normal(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals())
        assert state.capabilities["ai-lab-runtime"] == "allowed"

    def test_deployment_review_requires_approval_in_normal(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals())
        assert state.capabilities["deployment-review"] == "requires_approval"

    def test_marketplace_blocked_in_degraded(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals(degradation_level="HEAVY"))
        assert state.capabilities["marketplace-operator"] == "blocked"

    def test_observability_allowed_in_degraded(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals(degradation_level="HEAVY"))
        assert state.capabilities["observability"] == "allowed"

    def test_incident_response_allowed_in_lockdown(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals(emergency_mode=True))
        assert state.capabilities["incident-response"] == "allowed"

    def test_gitnexus_blocked_in_lockdown(self):
        gr = GovernanceResolver()
        state = gr.resolve(TriggerSignals(emergency_mode=True))
        assert state.capabilities["gitnexus-analysis"] == "blocked"


class TestGovernanceAntiFlapping:
    def test_anti_flap_prevents_rapid_transition(self, monkeypatch):
        gr = GovernanceResolver(anti_flap_seconds=9999)
        state1 = gr.resolve(TriggerSignals(slo_state="GREEN"))
        assert state1.mode == "NORMAL"
        state2 = gr.resolve(TriggerSignals(slo_state="RED"))
        assert state2.mode == "NORMAL"
        assert state2.transition_count == 0

    def test_transition_count_increments(self, monkeypatch):
        gr = GovernanceResolver(anti_flap_seconds=0)
        state1 = gr.resolve(TriggerSignals(slo_state="GREEN"))
        assert state1.mode == "NORMAL"
        state2 = gr.resolve(TriggerSignals(slo_state="RED"))
        assert state2.mode == "ELEVATED"
        assert state2.transition_count == 1

    def test_no_transition_when_same_mode(self, monkeypatch):
        gr = GovernanceResolver(anti_flap_seconds=0)
        state1 = gr.resolve(TriggerSignals(slo_state="GREEN"))
        state2 = gr.resolve(TriggerSignals(slo_state="GREEN"))
        assert state2.mode == "NORMAL"
        assert state2.transition_count == 0


class TestGovernanceTransitionRules:
    def test_transition_allowed(self):
        from runtime.hermes.governance.resolver import TRANSITION_RULES
        assert TRANSITION_RULES[("NORMAL", "ELEVATED")]["allowed"]
        assert TRANSITION_RULES[("NORMAL", "DEGRADED")]["allowed"]
        assert TRANSITION_RULES[("NORMAL", "LOCKDOWN")]["allowed"]
        assert TRANSITION_RULES[("ELEVATED", "NORMAL")]["allowed"]

    def test_lockdown_exit_requires_manual(self):
        from runtime.hermes.governance.resolver import TRANSITION_RULES
        assert not TRANSITION_RULES[("LOCKDOWN", "NORMAL")]["allowed"]
        assert not TRANSITION_RULES[("LOCKDOWN", "ELEVATED")]["allowed"]
        assert not TRANSITION_RULES[("LOCKDOWN", "DEGRADED")]["allowed"]


class TestGovernanceValidation:
    def test_validation_has_governance_checks(self):
        registry = load_all()
        result = validate_all(registry)
        gov_errors = [e for e in result.errors if "governance" in e.field or e.source == "governance/modes.json"]
        gov_warnings = [w for w in result.warnings if "governance" in w.field]
        assert len(gov_errors) == 0
        assert len(gov_warnings) == 0


class TestGovernanceStatusReport:
    def test_status_includes_governance_mode(self):
        report = build_status_report()
        assert report.governance_mode is not None
        assert report.governance_mode == "NORMAL"

    def test_status_includes_transition_count(self):
        report = build_status_report()
        assert report.governance_transition_count >= 0

    def test_status_json_has_governance_fields(self):
        from runtime.hermes.status import status_json
        import json
        data = json.loads(status_json())
        assert "governance_mode" in data
        assert "governance_transition_count" in data
        assert data["governance_mode"] == "NORMAL"


class TestGovernanceSchema:
    def test_schema_json_exists(self):
        path = os.path.join(HERMES_DIR, "governance", "schema.json")
        assert os.path.exists(path)

    def test_schema_valid_json(self):
        path = os.path.join(HERMES_DIR, "governance", "schema.json")
        with open(path, encoding="utf-8") as f:
            schema = json.load(f)
        assert schema["$schema"]
        assert schema["title"] == "GovernanceConfig"
