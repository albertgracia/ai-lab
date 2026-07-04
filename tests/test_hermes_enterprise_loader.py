import json
import os
import pytest

from runtime.hermes.loader import (
    load_all, load_soul, load_capabilities, load_operators,
    load_hooks, load_mcp_servers,
)
from runtime.hermes.validation import validate_all
from runtime.hermes.status import build_status_report, status_json
from runtime.hermes.models import StatusReport, ValidationResult


class TestSoulLoader:
    def test_soul_identity_loaded(self):
        soul = load_soul()
        assert "identity" in soul
        identity = soul["identity"]
        assert isinstance(identity, dict)
        assert identity.get("name") == "Hermes"

    def test_soul_truth_model_loaded(self):
        soul = load_soul()
        assert "truth_model" in soul
        truth = soul["truth_model"]
        assert "truth_levels" in truth
        assert truth.get("evidence_required") is True

    def test_soul_protocols_loaded(self):
        soul = load_soul()
        assert "protocols" in soul
        protocols = soul["protocols"]
        assert "protocols" in protocols

    def test_soul_boundaries_loaded(self):
        soul = load_soul()
        assert "boundaries" in soul
        boundaries = soul["boundaries"]
        assert "forbidden_actions" in boundaries
        assert "read_only_allowed" in boundaries

    def test_soul_domains_loaded(self):
        soul = load_soul()
        assert "domains" in soul
        domains = soul["domains"]
        assert "domains" in domains
        domain_dict = domains["domains"]
        assert len(domain_dict) >= 3
        assert "ai_lab" in domain_dict
        assert domain_dict["ai_lab"]["description"]


class TestCapabilityLoader:
    def test_capabilities_count(self):
        caps = load_capabilities()
        assert len(caps) == 6

    def test_capabilities_have_ids(self):
        caps = load_capabilities()
        ids = [c.id for c in caps]
        assert "ai-lab-runtime" in ids
        assert "marketplace-operator" in ids
        assert "observability" in ids
        assert "gitnexus-analysis" in ids
        assert "deployment-review" in ids
        assert "incident-response" in ids

    def test_all_capabilities_read_only(self):
        caps = load_capabilities()
        for cap in caps:
            perms = cap.permissions
            assert perms.get("read_only") is True, f"Capability {cap.id} is not read_only"

    def test_capability_required_mcp_valid(self):
        caps = load_capabilities()
        for cap in caps:
            for mcp in cap.required_mcp:
                assert isinstance(mcp, str) and len(mcp) > 0


class TestMCPServerLoader:
    def test_mcp_servers_count(self):
        servers = load_mcp_servers()
        assert len(servers) == 5

    def test_mcp_servers_have_ids(self):
        servers = load_mcp_servers()
        ids = [s.id for s in servers]
        assert "gitnexus" in ids
        assert "ailab-runtime-mcp" in ids
        assert "filesystem" in ids
        assert "prometheus" in ids
        assert "marketplace-mcp" in ids

    def test_active_servers_have_tools(self):
        servers = load_mcp_servers()
        for s in servers:
            if s.status == "active":
                assert len(s.tools) > 0, f"Active server {s.id} has no tools"

    def test_mcp_tool_read_only_flag(self):
        servers = load_mcp_servers()
        for s in servers:
            for t in s.tools:
                assert isinstance(t.read_only, bool)


class TestOperatorLoader:
    def test_operators_count(self):
        ops = load_operators()
        assert len(ops) == 5

    def test_operators_have_ids(self):
        ops = load_operators()
        ids = [o.id for o in ops]
        assert "runtime-health-check" in ids
        assert "marketplace-audit" in ids
        assert "observability-query" in ids
        assert "deployment-review" in ids
        assert "incident-triage" in ids

    def test_no_operator_is_execute(self):
        ops = load_operators()
        for op in ops:
            assert op.execution_mode in ("readonly", "advisory"), f"Operator {op.id} mode is {op.execution_mode}"


class TestHookLoader:
    def test_hooks_count(self):
        hooks = load_hooks()
        assert len(hooks) == 9

    def test_all_hooks_disabled(self):
        hooks = load_hooks()
        for hook in hooks:
            assert hook.enabled is False, f"Hook {hook.id} is enabled"

    def test_all_hooks_declarative_only(self):
        hooks = load_hooks()
        for hook in hooks:
            assert hook.mode == "declarative_only", f"Hook {hook.id} mode is {hook.mode}"

    def test_hooks_have_lifecycle_events(self):
        hooks = load_hooks()
        events = {h.lifecycle_event for h in hooks}
        expected = {
            "before_request", "after_request",
            "before_tool", "after_tool",
            "before_write", "after_write",
            "on_error", "on_incident", "on_shutdown",
        }
        assert events == expected


class TestValidation:
    def test_validation_passes_with_zero_errors(self):
        registry = load_all()
        result = validate_all(registry)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_validation_operator_capabilities_exist(self):
        registry = load_all()
        result = validate_all(registry)
        operator_errors = [e for e in result.errors if "capabilities" in e.field]
        assert len(operator_errors) == 0

    def test_validation_no_unknown_domains(self):
        registry = load_all()
        result = validate_all(registry)
        domain_errors = [e for e in result.errors if "domains" in e.field]
        assert len(domain_errors) == 0


class TestStatusReport:
    def test_status_report_structure(self):
        report = build_status_report()
        assert isinstance(report, StatusReport)
        assert report.registries_loaded is True
        assert report.soul_loaded is True
        assert report.capabilities_count == 6
        assert report.operators_count == 5
        assert report.hooks_count == 9
        assert report.mcp_servers_count == 5
        assert report.enforcement_active is False

    def test_status_json_output(self):
        js = status_json()
        data = json.loads(js)
        assert data["registries_loaded"] is True
        assert data["soul_loaded"] is True
        assert data["capabilities_count"] == 6
        assert data["enforcement_active"] is False
        assert isinstance(data["errors"], list)
        assert isinstance(data["warnings"], list)

    def test_enforcement_active_is_false(self):
        report = build_status_report()
        assert report.enforcement_active is False


class TestNoSideEffects:
    def test_loader_does_not_modify_files(self):
        import hashlib

        def md5_of(path):
            with open(path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()

        files_before = {}
        for root, dirs, fnames in os.walk("runtime/hermes"):
            for fname in fnames:
                fpath = os.path.join(root, fname)
                files_before[fpath] = md5_of(fpath)

        load_all()

        for fpath, md5_before in files_before.items():
            assert md5_of(fpath) == md5_before, f"File {fpath} was modified by loader"
