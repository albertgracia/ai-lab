import json
import os
from http.server import HTTPServer
from threading import Thread
from urllib.request import urlopen, Request
from urllib.error import URLError

import pytest

from runtime.hermes.enterprise_status import build_enterprise_status, enterprise_status_json
from runtime.hermes.status import status_json


HERMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "hermes")


class TestEnterpriseStatusStructure:
    def test_build_returns_dict(self):
        data = build_enterprise_status()
        assert isinstance(data, dict)

    def test_has_service_field(self):
        data = build_enterprise_status()
        assert data["service"] == "Hermes Enterprise"

    def test_has_version_field(self):
        data = build_enterprise_status()
        assert data["version"] == "1.0"

    def test_has_build_field(self):
        data = build_enterprise_status()
        assert data["build"] == "CP-HERMES-ENTERPRISE-CORE-01"


class TestEnterpriseStatusGit:
    def test_has_git_block(self):
        data = build_enterprise_status()
        assert "git" in data
        assert "head" in data["git"]
        assert "branch" in data["git"]
        assert "dirty" in data["git"]

    def test_git_head_is_string(self):
        data = build_enterprise_status()
        assert isinstance(data["git"]["head"], str)
        assert len(data["git"]["head"]) > 0

    def test_git_branch_is_string(self):
        data = build_enterprise_status()
        assert isinstance(data["git"]["branch"], str)
        assert len(data["git"]["branch"]) > 0

    def test_git_dirty_is_bool(self):
        data = build_enterprise_status()
        assert isinstance(data["git"]["dirty"], bool)


class TestEnterpriseStatusEnterprise:
    def test_has_enterprise_block(self):
        data = build_enterprise_status()
        assert "enterprise" in data

    def test_enterprise_core_version(self):
        data = build_enterprise_status()
        assert data["enterprise"]["core_version"] == "CP-HERMES-ENTERPRISE-CORE-01"

    def test_foundation_complete(self):
        data = build_enterprise_status()
        assert data["enterprise"]["foundation_complete"] is True

    def test_schema_version(self):
        data = build_enterprise_status()
        assert data["enterprise"]["schema_version"] == "1.0"

    def test_registries_loaded(self):
        data = build_enterprise_status()
        assert data["enterprise"]["registries_loaded"] is True

    def test_initialized(self):
        data = build_enterprise_status()
        assert data["enterprise"]["initialized"] is True


class TestEnterpriseStatusSoul:
    def test_has_soul_block(self):
        data = build_enterprise_status()
        assert "soul" in data

    def test_soul_loaded(self):
        data = build_enterprise_status()
        assert data["soul"]["loaded"] is True

    def test_soul_version(self):
        data = build_enterprise_status()
        assert data["soul"]["version"] == "1.0.0"

    def test_soul_has_truth_model(self):
        data = build_enterprise_status()
        tm = data["soul"]["truth_model"]
        assert isinstance(tm, dict)
        assert "truth_levels" in tm
        assert "OBSERVADO" in tm["truth_levels"]
        assert "INFERIDO" in tm["truth_levels"]
        assert "SUPUESTO" in tm["truth_levels"]


class TestEnterpriseStatusCapabilities:
    def test_has_capabilities_block(self):
        data = build_enterprise_status()
        assert "capabilities" in data

    def test_capabilities_total(self):
        data = build_enterprise_status()
        assert data["capabilities"]["total"] == 6

    def test_capabilities_valid(self):
        data = build_enterprise_status()
        assert data["capabilities"]["valid"] is True

    def test_capabilities_dependency_graph_ok(self):
        data = build_enterprise_status()
        assert data["capabilities"]["dependency_graph_ok"] is True


class TestEnterpriseStatusOperators:
    def test_has_operators_block(self):
        data = build_enterprise_status()
        assert "operators" in data

    def test_operators_total(self):
        data = build_enterprise_status()
        assert data["operators"]["total"] == 5

    def test_operators_valid(self):
        data = build_enterprise_status()
        assert data["operators"]["valid"] is True


class TestEnterpriseStatusHooks:
    def test_has_hooks_block(self):
        data = build_enterprise_status()
        assert "hooks" in data

    def test_hooks_total(self):
        data = build_enterprise_status()
        assert data["hooks"]["total"] == 9

    def test_hooks_enabled(self):
        data = build_enterprise_status()
        assert data["hooks"]["enabled"] == 0

    def test_hooks_enforcement(self):
        data = build_enterprise_status()
        assert data["hooks"]["enforcement"] is False


class TestEnterpriseStatusMCP:
    def test_has_mcp_block(self):
        data = build_enterprise_status()
        assert "mcp" in data

    def test_mcp_total(self):
        data = build_enterprise_status()
        assert data["mcp"]["total"] == 5

    def test_mcp_configured(self):
        data = build_enterprise_status()
        assert data["mcp"]["configured"] == 5

    def test_mcp_has_servers_list(self):
        data = build_enterprise_status()
        assert isinstance(data["mcp"]["servers"], list)
        assert len(data["mcp"]["servers"]) == 5

    def test_mcp_servers_have_ids(self):
        data = build_enterprise_status()
        ids = [s["id"] for s in data["mcp"]["servers"]]
        assert "gitnexus" in ids
        assert "ailab-runtime-mcp" in ids
        assert "filesystem" in ids


class TestEnterpriseStatusGovernance:
    def test_has_governance_block(self):
        data = build_enterprise_status()
        assert "governance" in data

    def test_governance_mode_normal(self):
        data = build_enterprise_status()
        assert data["governance"]["mode"] == "NORMAL"

    def test_governance_enforcement_disabled(self):
        data = build_enterprise_status()
        assert data["governance"]["enforcement_active"] is False

    def test_governance_anti_flapping(self):
        data = build_enterprise_status()
        assert data["governance"]["anti_flapping"] is True

    def test_governance_has_modes(self):
        data = build_enterprise_status()
        assert "NORMAL" in data["governance"]["modes"]
        assert "ELEVATED" in data["governance"]["modes"]
        assert "DEGRADED" in data["governance"]["modes"]
        assert "LOCKDOWN" in data["governance"]["modes"]


class TestEnterpriseStatusArchitecture:
    def test_has_architecture_block(self):
        data = build_enterprise_status()
        assert "architecture" in data

    def test_architecture_enterprise_phase(self):
        data = build_enterprise_status()
        assert data["architecture"]["enterprise_phase"] == "CORE"

    def test_architecture_next_phase(self):
        data = build_enterprise_status()
        assert data["architecture"]["next_phase"] == "E08"

    def test_architecture_readiness(self):
        data = build_enterprise_status()
        assert data["architecture"]["readiness"] == "READY"

    def test_architecture_compatibility_astro(self):
        data = build_enterprise_status()
        assert data["architecture"]["compatibility"]["astro"] is True

    def test_architecture_compatibility_marketplace(self):
        data = build_enterprise_status()
        assert data["architecture"]["compatibility"]["marketplace"] is True

    def test_architecture_compatibility_gitnexus(self):
        data = build_enterprise_status()
        assert data["architecture"]["compatibility"]["gitnexus"] is True

    def test_architecture_compatibility_mcp(self):
        data = build_enterprise_status()
        assert data["architecture"]["compatibility"]["mcp"] is True


class TestEnterpriseStatusTests:
    def test_has_tests_block(self):
        data = build_enterprise_status()
        assert "tests" in data

    def test_tests_passed(self):
        data = build_enterprise_status()
        assert data["tests"]["passed"] >= 113

    def test_tests_failed(self):
        data = build_enterprise_status()
        assert data["tests"]["failed"] == 0


class TestEnterpriseStatusHealth:
    def test_has_status_block(self):
        data = build_enterprise_status()
        assert "status" in data

    def test_status_healthy(self):
        data = build_enterprise_status()
        assert data["status"]["healthy"] is True

    def test_status_errors(self):
        data = build_enterprise_status()
        assert isinstance(data["status"]["errors"], list)
        assert len(data["status"]["errors"]) == 0

    def test_status_warnings(self):
        data = build_enterprise_status()
        assert isinstance(data["status"]["warnings"], list)


class TestEnterpriseStatusJSON:
    def test_json_valid(self):
        js = enterprise_status_json()
        data = json.loads(js)
        assert isinstance(data, dict)
        assert data["service"] == "Hermes Enterprise"

    def test_json_matches_build(self):
        js = enterprise_status_json()
        data = json.loads(js)
        build = build_enterprise_status()
        assert data["governance"]["mode"] == build["governance"]["mode"]
        assert data["status"]["healthy"] == build["status"]["healthy"]
        assert data["enterprise"]["core_version"] == build["enterprise"]["core_version"]

    def test_json_indent(self):
        js = enterprise_status_json(indent=4)
        assert "    " in js


class TestEnterpriseStatusComparison:
    def test_reuses_core_status(self):
        es = build_enterprise_status()
        assert es["enterprise"]["registries_loaded"] is True
        assert es["soul"]["loaded"] is True

    def test_enforcement_active_false(self):
        es = build_enterprise_status()
        assert es["governance"]["enforcement_active"] is False


@pytest.fixture(scope="module")
def server_url():
    from runtime.hermes.endpoint import HermesStatusHandler
    server = HTTPServer(("127.0.0.1", 0), HermesStatusHandler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield url
    server.shutdown()


class TestEnterpriseEndpoint:
    def test_endpoint_200(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        assert resp.status == 200
        assert resp.headers["Content-Type"] == "application/json"

    def test_endpoint_returns_valid_json(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["service"] == "Hermes Enterprise"

    def test_endpoint_health(self, server_url):
        req = Request(f"{server_url}/health")
        resp = urlopen(req, timeout=5)
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        assert data["status"] == "ok"

    def test_endpoint_404(self, server_url):
        with pytest.raises(URLError) as exc:
            req = Request(f"{server_url}/unknown")
            urlopen(req, timeout=5)

    def test_endpoint_governance_mode(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["governance"]["mode"] == "NORMAL"

    def test_endpoint_hooks_enabled(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["hooks"]["enabled"] == 0

    def test_endpoint_enforcement_disabled(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["governance"]["enforcement_active"] is False

    def test_endpoint_foundation_complete(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["enterprise"]["foundation_complete"] is True

    def test_endpoint_core_version(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["enterprise"]["core_version"] == "CP-HERMES-ENTERPRISE-CORE-01"

    def test_endpoint_architecture_phase(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["architecture"]["enterprise_phase"] == "CORE"

    def test_endpoint_architecture_next_phase(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["architecture"]["next_phase"] == "E08"

    def test_endpoint_architecture_readiness(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["architecture"]["readiness"] == "READY"

    def test_endpoint_architecture_compatibility(self, server_url):
        req = Request(f"{server_url}/hermes/status")
        resp = urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        assert data["architecture"]["compatibility"]["astro"] is True
        assert data["architecture"]["compatibility"]["marketplace"] is True
        assert data["architecture"]["compatibility"]["gitnexus"] is True
        assert data["architecture"]["compatibility"]["mcp"] is True
