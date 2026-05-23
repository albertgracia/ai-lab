"""DEV-36X: Codebase Memory Integration tests."""

from __future__ import annotations

import json
import os
import sys
import threading

sys.path.insert(0, "/opt/ai-lab")

from runtime.codebase import (
    CODEBASE_CONTRACT_VERSION,
    load_codebase_memory,
    build_codebase_summary,
    build_codebase_dependency_graph,
    build_codebase_module_topology,
    build_codebase_ownership,
    build_codebase_blast_radius_analysis,
    build_codebase_structural_risks,
    build_codebase_score,
    get_codebase_memory_freshness,
    get_codebase_cache_state,
    reset_codebase_memory_cache,
)
from runtime.codebase.gitnexus_memory import (
    _scan_runtime_modules,
    _build_import_graph,
    _build_ownership,
    _build_blast_radius,
    _detect_structural_risks,
    _detect_hotspots,
    _compute_score,
    _path_to_domain,
)
from runtime.codebase.contracts import OWNERSHIP_DOMAINS, EXCLUDED_DIRS, RUNTIME_ROOT, CodebaseModule, DependencyEdge


# ── Contract ─────────────────────────────────────────────────────────

def test_contract_version():
    assert CODEBASE_CONTRACT_VERSION == "DEV-36X"


def test_ownership_domains_defined():
    assert len(OWNERSHIP_DOMAINS) >= 6
    for domain, prefixes in OWNERSHIP_DOMAINS.items():
        assert isinstance(domain, str)
        assert isinstance(prefixes, list)
        assert len(prefixes) > 0


def test_excluded_dirs_defined():
    assert "__pycache__" in EXCLUDED_DIRS
    assert "__init__" not in EXCLUDED_DIRS


def test_runtime_root_exists():
    root = os.path.join("/opt/ai-lab", "runtime")
    assert os.path.isdir(root)


# ── Core module: scan ──────────────────────────────────────────────

def test_scan_runtime_modules_returns_dict():
    modules = _scan_runtime_modules()
    assert isinstance(modules, dict)
    assert len(modules) > 5


def test_scan_runtime_modules_has_key_modules():
    modules = _scan_runtime_modules()
    names = list(modules.keys())
    assert "gateway" in names
    assert "codebase" in names
    assert "incidents" in names
    assert "governance" in names
    assert "telemetry" in names
    assert "validation" in names


def test_scan_runtime_modules_has_file_counts():
    modules = _scan_runtime_modules()
    nonzero = [name for name, mod in modules.items() if mod.file_count > 0]
    assert len(nonzero) >= len(modules) - 4
    for name, mod in modules.items():
        assert mod.path.startswith("runtime/")


# ── Path to domain mapping ─────────────────────────────────────────

def test_path_to_domain_maps_correctly():
    assert _path_to_domain("runtime/gateway/openai_gateway.py") == "gateway"
    assert _path_to_domain("runtime/telemetry/prometheus_metrics.py") == "telemetry"
    assert _path_to_domain("runtime/governance/runtime_governance_registry.py") == "governance"
    assert _path_to_domain("runtime/codebase/__init__.py") == "codebase"
    assert _path_to_domain("runtime/validation/runtime_validation_framework.py") == "validation"
    assert _path_to_domain("runtime/incidents/incident_intelligence.py") == "incidents"
    assert _path_to_domain("runtime/reporting/reporting_engine.py") == "reporting"


def test_path_to_domain_unknown():
    assert _path_to_domain("some/other/path.py") == "other"


# ── Import graph ──────────────────────────────────────────────────

def test_build_import_graph_returns_edges():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    assert isinstance(edges, list)
    assert len(edges) > 0
    for e in edges:
        assert isinstance(e, DependencyEdge)
        assert e.source in modules
        assert e.target in modules


def test_import_graph_contains_expected():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    edge_set = {(e.source, e.target) for e in edges}
    has_codebase = any(s == "codebase" or t == "codebase" for s, t in edge_set)
    assert has_codebase, "codebase module should appear in dependency graph"


# ── Ownership ─────────────────────────────────────────────────────

def test_build_ownership_returns_entries():
    modules = _scan_runtime_modules()
    ownership = _build_ownership(modules)
    assert isinstance(ownership, list)
    assert len(ownership) >= 1
    for o in ownership:
        assert o.file_count > 0
        assert len(o.paths) > 0


# ── Blast radius ─────────────────────────────────────────────────

def test_build_blast_radius_returns_results():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    results = _build_blast_radius(modules, edges)
    assert isinstance(results, list)
    for r in results:
        assert r.total_impacted >= 0
        assert r.severity in ("low", "medium", "high")


# ── Structural risks ─────────────────────────────────────────────

def test_detect_structural_risks_returns_list():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    blast = _build_blast_radius(modules, edges)
    risks = _detect_structural_risks(modules, edges, blast)
    assert isinstance(risks, list)
    for r in risks:
        assert r.risk_type in ("high_coupling", "high_reverse_coupling", "wide_blast_radius", "authority_dependency_spread")


def test_detect_hotspots_returns_list():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    hotspots = _detect_hotspots(modules, edges)
    assert isinstance(hotspots, list)
    assert len(hotspots) <= 5


# ── Score ─────────────────────────────────────────────────────────

def test_compute_score_returns_dict():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    risks = _detect_structural_risks(modules, edges, _build_blast_radius(modules, edges))
    score = _compute_score(modules, risks, edges)
    assert isinstance(score, dict)
    assert "structural_health_score" in score
    assert "level" in score
    assert 10.0 <= score["structural_health_score"] <= 100.0


def test_compute_score_deterministic():
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    risks = _detect_structural_risks(modules, edges, _build_blast_radius(modules, edges))
    s1 = _compute_score(modules, risks, edges)
    s2 = _compute_score(modules, risks, edges)
    assert s1 == s2


# ── Load full memory ─────────────────────────────────────────────

def test_load_codebase_memory_returns_valid():
    mem = load_codebase_memory()
    assert mem.contract_version == CODEBASE_CONTRACT_VERSION
    assert len(mem.modules) > 5
    assert len(mem.dependency_edges) > 0
    assert len(mem.ownership) >= 1
    assert mem.score["structural_health_score"] >= 10.0
    assert mem.determinant_signature is not None


def test_load_codebase_memory_deterministic():
    reset_codebase_memory_cache()
    m1 = load_codebase_memory()
    reset_codebase_memory_cache()
    m2 = load_codebase_memory()
    assert m1.determinant_signature == m2.determinant_signature


# ── Public APIs ──────────────────────────────────────────────────

def test_build_codebase_summary_returns_valid():
    reset_codebase_memory_cache()
    s = build_codebase_summary()
    assert s["contract_version"] == CODEBASE_CONTRACT_VERSION
    assert "score" in s
    assert "summary" in s
    assert "freshness" in s


def test_build_codebase_dependency_graph_returns_valid():
    reset_codebase_memory_cache()
    g = build_codebase_dependency_graph()
    assert "edges" in g
    assert "modules" in g
    assert g["modules_total"] > 0


def test_build_codebase_module_topology_returns_valid():
    reset_codebase_memory_cache()
    t = build_codebase_module_topology()
    assert "modules_total" in t
    assert "edges_total" in t
    assert t["modules_total"] > 0


def test_build_codebase_ownership_returns_valid():
    reset_codebase_memory_cache()
    o = build_codebase_ownership()
    assert "domains" in o
    assert o["domains_total"] >= 1


def test_build_codebase_blast_radius_analysis_returns_valid():
    reset_codebase_memory_cache()
    br = build_codebase_blast_radius_analysis()
    assert "results" in br
    assert "results_total" in br


def test_build_codebase_blast_radius_analysis_with_filter():
    reset_codebase_memory_cache()
    br = build_codebase_blast_radius_analysis(module_path="gateway")
    for r in br["results"]:
        assert "gateway" in r.get("module_path", "")


def test_build_codebase_structural_risks_returns_valid():
    reset_codebase_memory_cache()
    r = build_codebase_structural_risks()
    assert "risks" in r
    assert "score" in r


def test_build_codebase_score_returns_valid():
    reset_codebase_memory_cache()
    s = build_codebase_score()
    assert "score" in s
    assert s["score"]["structural_health_score"] >= 10.0


def test_get_codebase_memory_freshness_returns_valid():
    reset_codebase_memory_cache()
    f = get_codebase_memory_freshness()
    assert "freshness" in f
    assert "generated_at" in f


def test_get_codebase_cache_state_returns_valid():
    reset_codebase_memory_cache()
    c = get_codebase_cache_state()
    assert "cache_entries" in c
    assert "cache_hits" in c
    assert "cache_misses" in c


# ── Cache determinism ────────────────────────────────────────────

def test_cache_determinism_across_calls():
    reset_codebase_memory_cache()
    s1 = build_codebase_summary()
    s2 = build_codebase_summary()
    assert s1["determinant_signature"] == s2["determinant_signature"]


# ── Gateway integration (smoke) ──────────────────────────────────

def test_gateway_codebase_routes_defined():
    from runtime.codebase.gitnexus_memory import build_codebase_summary, build_codebase_dependency_graph
    s = build_codebase_summary()
    g = build_codebase_dependency_graph()
    assert "determinant_signature" in s
    assert "determinant_signature" in g
