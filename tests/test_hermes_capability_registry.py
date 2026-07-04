import json
import pytest

from runtime.hermes.loader import load_all
from runtime.hermes.validation import (
    validate_all, build_capability_dependency_graph,
)


class TestCapabilityIdsUnique:
    def test_all_ids_unique(self):
        registry = load_all()
        ids = [c.id for c in registry.capabilities]
        assert len(ids) == len(set(ids))


class TestCapabilityRequiredFields:
    def test_all_have_purpose(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert cap.purpose, f"Capability {cap.id} has no purpose"

    def test_all_have_domains(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert cap.domains, f"Capability {cap.id} has no domains"

    def test_all_have_forbidden_actions(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert cap.forbidden_actions, f"Capability {cap.id} has no forbidden actions"

    def test_all_have_evidence_requirements(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert isinstance(cap.evidence_requirements, dict)
            assert cap.evidence_requirements, f"Capability {cap.id} has empty evidence_requirements"

    def test_all_have_reports(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert cap.reports, f"Capability {cap.id} has no reports"


class TestCapabilityPermissions:
    def test_all_have_read_only(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert "read_only" in cap.permissions, f"Capability {cap.id} missing read_only"
            assert cap.permissions["read_only"] is True, f"Capability {cap.id} not read_only"

    def test_all_have_governance_levels(self):
        registry = load_all()
        for cap in registry.capabilities:
            assert "governance_levels" in cap.permissions, f"Capability {cap.id} missing governance_levels"


class TestCapabilityEvidence:
    def test_all_have_min_confidence(self):
        registry = load_all()
        for cap in registry.capabilities:
            ev = cap.evidence_requirements
            assert "min_confidence" in ev, f"Capability {cap.id} missing min_confidence"

    def test_all_have_require_citations(self):
        registry = load_all()
        for cap in registry.capabilities:
            ev = cap.evidence_requirements
            assert "require_citations" in ev, f"Capability {cap.id} missing require_citations"


class TestCapabilityDependencies:
    def test_all_dependencies_exist(self):
        registry = load_all()
        cap_ids = {c.id for c in registry.capabilities}
        for cap in registry.capabilities:
            for dep in cap.dependencies:
                assert dep in cap_ids, f"Capability {cap.id} depends on '{dep}' which does not exist"

    def test_no_circular_dependencies(self):
        registry = load_all()
        graph = build_capability_dependency_graph(registry)
        assert not graph.cycles_detected, f"Circular dependencies detected: {graph.cycles}"
        assert len(graph.cycles) == 0

    def test_deployment_review_depends_on_ai_lab_and_gitnexus(self):
        registry = load_all()
        for cap in registry.capabilities:
            if cap.id == "deployment-review":
                assert "ai-lab-runtime" in cap.dependencies
                assert "gitnexus-analysis" in cap.dependencies
                return
        pytest.fail("Capability deployment-review not found")

    def test_incident_response_depends_on_ai_lab_and_observability(self):
        registry = load_all()
        for cap in registry.capabilities:
            if cap.id == "incident-response":
                assert "ai-lab-runtime" in cap.dependencies
                assert "observability" in cap.dependencies
                return
        pytest.fail("Capability incident-response not found")


class TestCapabilityDomains:
    def test_no_unknown_domains(self):
        registry = load_all()
        valid = {"ai-lab", "marketplace", "observability", "gitnexus", "windows"}
        for cap in registry.capabilities:
            for d in cap.domains:
                assert d in valid, f"Capability {cap.id} has unknown domain '{d}'"


class TestCapabilityMCP:
    def test_required_mcp_servers_exist(self):
        registry = load_all()
        mcp_ids = {s.id for s in registry.mcp_servers}
        for cap in registry.capabilities:
            for mcp in cap.required_mcp:
                assert mcp in mcp_ids, f"Capability {cap.id} requires MCP '{mcp}' not in registry"


class TestCapabilityInputsOutputs:
    def test_all_have_inputs(self):
        registry = load_all()
        for cap in registry.capabilities:
            inputs = cap.raw.get("inputs", {})
            assert isinstance(inputs, dict), f"Capability {cap.id} inputs not a dict"

    def test_all_have_outputs(self):
        registry = load_all()
        for cap in registry.capabilities:
            outputs = cap.raw.get("outputs", {})
            assert isinstance(outputs, dict), f"Capability {cap.id} outputs not a dict"
            assert len(outputs) > 0, f"Capability {cap.id} has no outputs"


class TestCriticalCapabilities:
    def test_all_six_critical_capabilities_present(self):
        registry = load_all()
        ids = {c.id for c in registry.capabilities}
        required = {
            "ai-lab-runtime", "gitnexus-analysis", "observability",
            "marketplace-operator", "deployment-review", "incident-response",
        }
        missing = required - ids
        assert not missing, f"Missing critical capabilities: {missing}"


class TestDependencyGraph:
    def test_graph_has_all_nodes(self):
        registry = load_all()
        graph = build_capability_dependency_graph(registry)
        assert len(graph.nodes) == 6
        assert "ai-lab-runtime" in graph.nodes

    def test_graph_edges_correct_count(self):
        registry = load_all()
        graph = build_capability_dependency_graph(registry)
        assert len(graph.edges) == 5

    def test_no_cycles(self):
        registry = load_all()
        graph = build_capability_dependency_graph(registry)
        assert not graph.cycles_detected


class TestValidationIntegration:
    def test_validation_zero_errors(self):
        registry = load_all()
        result = validate_all(registry)
        cap_errors = [e for e in result.errors if e.source.startswith("capabilities/")]
        assert len(cap_errors) == 0

    def test_status_json_has_capability_fields(self):
        from runtime.hermes.status import status_json
        js = status_json()
        data = json.loads(js)
        assert "capability_validation" in data
        assert "capability_dependency_graph" in data
        assert "capability_cycles_detected" in data
        assert data["capability_cycles_detected"] is False
        assert data["capability_validation"]["total"] == 6
        assert data["capability_validation"]["critical_present"] is True
