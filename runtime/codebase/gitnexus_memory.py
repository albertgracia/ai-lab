from __future__ import annotations

import ast
import json
import os
import pathlib
import re
import threading
import time
from typing import Any

from runtime.codebase.contracts import (
    CODEBASE_CONTRACT_VERSION,
    OWNERSHIP_DOMAINS,
    EXCLUDED_DIRS,
    GITNEXUS_CONFIG_PATH,
    GITNEXUS_META_PATH,
    RUNTIME_ROOT,
    CodebaseModule,
    DependencyEdge,
    OwnershipEntry,
    BlastRadiusResult,
    StructuralRisk,
    CodebaseMemory,
    CodebaseTopology,
    _hash,
    _now,
    _strict_mode,
)


_CACHE_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}
_CACHE_HITS = 0
_CACHE_MISSES = 0


def _get_cached(key: str, builder, *, ttl_s: int = 30) -> Any:
    global _CACHE_HITS, _CACHE_MISSES
    now = _now()
    with _CACHE_LOCK:
        ent = _CACHE.get(key)
        if ent is not None:
            age = now - float(ent.get("ts", 0.0))
            if age <= float(ent.get("ttl_s", ttl_s)):
                _CACHE_HITS += 1
                return ent.get("value")
    _CACHE_MISSES += 1
    val = builder()
    with _CACHE_LOCK:
        _CACHE[key] = {"value": val, "ts": now, "ttl_s": int(ttl_s)}
    return val


def _read_gitnexus_meta() -> dict[str, Any]:
    try:
        p = pathlib.Path(GITNEXUS_META_PATH)
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _scan_runtime_modules() -> dict[str, CodebaseModule]:
    root = pathlib.Path(RUNTIME_ROOT)
    if not root.is_dir():
        return {}
    modules: dict[str, CodebaseModule] = {}
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name in EXCLUDED_DIRS or name.startswith("."):
            continue
        py_files = sorted(
            str(f.relative_to(root.parent))
            for f in entry.rglob("*.py")
            if "__pycache__" not in str(f)
        )
        rel_path = f"runtime/{name}"
        domain = _path_to_domain(rel_path)
        modules[name] = CodebaseModule(
            path=rel_path,
            module_name=name,
            domain=domain,
            file_count=len(py_files),
            import_edges=py_files[:50],
        )
    return modules


def _path_to_domain(path: str) -> str:
    for domain, prefixes in OWNERSHIP_DOMAINS.items():
        for p in prefixes:
            if path.startswith(p):
                return domain
    return "other"


def _parse_imports(file_path: str) -> list[str]:
    try:
        tree = ast.parse(pathlib.Path(file_path).read_text(encoding="utf-8"))
    except Exception:
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                targets.append(node.module)
    return targets


def _build_import_graph(
    modules: dict[str, CodebaseModule],
) -> list[DependencyEdge]:
    edges: list[DependencyEdge] = []
    root = pathlib.Path(RUNTIME_ROOT)
    runtime_imports: dict[str, set[str]] = {}
    for mod_name, mod in modules.items():
        mod_dir = root / mod_name
        if not mod_dir.is_dir():
            continue
        imports: set[str] = set()
        for py_file in mod_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            for imp in _parse_imports(str(py_file)):
                if imp.startswith("runtime."):
                    parts = imp.split(".")
                    if len(parts) >= 2:
                        imports.add(parts[1])
        runtime_imports[mod_name] = {i for i in imports if i in modules}
    for source, targets in runtime_imports.items():
        for target in sorted(targets):
            edges.append(DependencyEdge(source=source, target=target, edge_type="import"))
    return edges


def _build_domain_dependency_matrix(
    modules: dict[str, CodebaseModule],
    edges: list[DependencyEdge],
) -> dict[str, list[str]]:
    domain_imports: dict[str, set[str]] = {}
    for mod in modules.values():
        d = mod.domain
        if d not in domain_imports:
            domain_imports[d] = set()
    for edge in edges:
        src_mod = modules.get(edge.source)
        tgt_mod = modules.get(edge.target)
        if src_mod and tgt_mod and src_mod.domain != tgt_mod.domain:
            domain_imports[src_mod.domain].add(tgt_mod.domain)
    return {k: sorted(v) for k, v in sorted(domain_imports.items()) if v}


def _build_ownership(modules: dict[str, CodebaseModule]) -> list[OwnershipEntry]:
    domain_map: dict[str, set[str]] = {}
    for mod in modules.values():
        d = mod.domain
        if d not in domain_map:
            domain_map[d] = set()
        domain_map[d].add(mod.path)
    result: list[OwnershipEntry] = []
    for d, ps in sorted(domain_map.items()):
        total_files = 0
        for p in ps:
            mod_name = p.split("/")[-1]
            m = modules.get(mod_name)
            if m is not None:
                total_files += m.file_count
        result.append(OwnershipEntry(domain=d, paths=sorted(ps), file_count=total_files))
    return result


def _build_blast_radius(
    modules: dict[str, CodebaseModule],
    edges: list[DependencyEdge],
) -> list[BlastRadiusResult]:
    results: list[BlastRadiusResult] = []
    dep_map: dict[str, set[str]] = {}
    for mod_name in modules:
        dep_map[mod_name] = set()
    for edge in edges:
        if edge.target in dep_map:
            dep_map[edge.source].add(edge.target)
    for mod_name in sorted(modules):
        impacted = set()
        impacted.add(mod_name)
        queue = [mod_name]
        visited = {mod_name}
        while queue:
            current = queue.pop(0)
            for dependent, deps in dep_map.items():
                if current in deps and dependent not in visited:
                    visited.add(dependent)
                    impacted.add(dependent)
                    queue.append(dependent)
        impacted.discard(mod_name)
        if not impacted:
            continue
        affected_domains = sorted(set(
            modules[i].domain for i in impacted if i in modules
        ))
        total = len(impacted)
        if total <= 2:
            sev = "low"
        elif total <= 5:
            sev = "medium"
        else:
            sev = "high"
        results.append(BlastRadiusResult(
            module_path=modules[mod_name].path,
            affected_domains=affected_domains,
            affected_modules=sorted(impacted),
            total_impacted=total,
            severity=sev,
        ))
    return results


def _detect_structural_risks(
    modules: dict[str, CodebaseModule],
    edges: list[DependencyEdge],
    blast_radius_results: list[BlastRadiusResult],
) -> list[StructuralRisk]:
    risks: list[StructuralRisk] = []
    dep_map: dict[str, set[str]] = {}
    reverse_map: dict[str, set[str]] = {}
    for mod_name in modules:
        dep_map[mod_name] = set()
        reverse_map[mod_name] = set()
    for edge in edges:
        if edge.target in dep_map:
            dep_map[edge.source].add(edge.target)
        if edge.source in reverse_map:
            reverse_map[edge.target].add(edge.source)
    for mod_name in sorted(modules):
        deps = dep_map.get(mod_name, set())
        if len(deps) >= 5:
            risks.append(StructuralRisk(
                risk_type="high_coupling",
                domain=modules[mod_name].domain,
                description=f"module {mod_name} imports {len(deps)} other modules",
                severity="medium",
                details={"module": mod_name, "dependency_count": len(deps), "dependencies": sorted(deps)},
            ))
        rdeps = reverse_map.get(mod_name, set())
        if len(rdeps) >= 5:
            risks.append(StructuralRisk(
                risk_type="high_reverse_coupling",
                domain=modules[mod_name].domain,
                description=f"module {mod_name} is imported by {len(rdeps)} other modules",
                severity="high",
                details={"module": mod_name, "reverse_dependency_count": len(rdeps), "dependents": sorted(rdeps)},
            ))
    for br in blast_radius_results:
        if br.severity == "high":
            risks.append(StructuralRisk(
                risk_type="wide_blast_radius",
                domain=modules.get(br.module_path.split("/")[-1], CodebaseModule("", "", "", 0)).domain if br.module_path.split("/")[-1] in modules else "unknown",
                description=f"module {br.module_path} impacts {br.total_impacted} modules on change",
                severity="high",
                details={"module": br.module_path, "impacted_total": br.total_impacted, "impacted": br.affected_modules},
            ))
    auth_deps = dep_map.get("authority", set())
    if len(auth_deps) >= 3:
        risks.append(StructuralRisk(
            risk_type="authority_dependency_spread",
            domain="authority",
            description=f"authority module imported by {len(auth_deps)} domains",
            severity="medium",
            details={"dependency_count": len(auth_deps), "dependents": sorted(auth_deps)},
        ))
    return risks


# Risk-type penalty weights (37D: grounded by operational risk)
#   wide_blast_radius: noise inherent to monorepo structure → 0 penalty
#   authority_dependency_spread: false positive by design → 0 penalty
#   high_coupling: expected coupling in 74-module codebase → reduced penalty
#   high_reverse_coupling: real operational coupling risk → full penalty
_REVERSE_COUPLING_PENALTY = 1.5   # per instance
_REVERSE_COUPLING_CAP = 40.0
_COUPLING_PENALTY = 0.5            # per instance
_COUPLING_CAP = 12.0


def _compute_score(
    modules: dict[str, CodebaseModule],
    risks: list[StructuralRisk],
    edges: list[DependencyEdge],
) -> dict[str, Any]:
    total_modules = len(modules)
    total_edges = len(edges)

    raw_high = sum(1 for r in risks if r.severity == "high")
    raw_medium = sum(1 for r in risks if r.severity == "medium")
    raw_low = sum(1 for r in risks if r.severity == "low")

    reverse_coupling = sum(1 for r in risks if r.risk_type == "high_reverse_coupling")
    forward_coupling = sum(1 for r in risks if r.risk_type == "high_coupling")
    blast_radius = sum(1 for r in risks if r.risk_type == "wide_blast_radius")
    auth_spread = sum(1 for r in risks if r.risk_type == "authority_dependency_spread")

    base = 100.0
    op_penalty = min(_REVERSE_COUPLING_CAP, reverse_coupling * _REVERSE_COUPLING_PENALTY)
    debt_penalty = min(_COUPLING_CAP, forward_coupling * _COUPLING_PENALTY)
    base -= op_penalty
    base -= debt_penalty

    if total_modules > 0:
        edge_density = total_edges / max(total_modules, 1)
        if edge_density > 5.0:
            base -= min(15.0, (edge_density - 5.0) * 3.0)

    score = max(10.0, min(100.0, base))
    level = "healthy" if score >= 70 else "degraded" if score >= 40 else "critical"

    return {
        "structural_health_score": round(score, 1),
        "level": level,
        "modules_total": total_modules,
        "edges_total": total_edges,
        "high_risks": raw_high,
        "medium_risks": raw_medium,
        "low_risks": raw_low,
        "total_findings": len(risks),
        "breakdown": {
            "operational_risk_points": round(op_penalty, 1),
            "controlled_debt_points": round(debt_penalty, 1),
            "noise_points_excluded": round(blast_radius + auth_spread, 1),
        },
        "risk_classification": {
            "operational_risk_count": reverse_coupling,
            "controlled_debt_count": forward_coupling,
            "noise_count": blast_radius + auth_spread,
        },
    }


def _detect_hotspots(
    modules: dict[str, CodebaseModule],
    edges: list[DependencyEdge],
) -> list[str]:
    dep_count: dict[str, int] = {}
    for mod_name in modules:
        dep_count[mod_name] = 0
    for edge in edges:
        if edge.target in dep_count:
            dep_count[edge.target] = dep_count.get(edge.target, 0) + 1
        if edge.source in dep_count:
            dep_count[edge.source] = dep_count.get(edge.source, 0)
    sorted_by_deps = sorted(dep_count.items(), key=lambda x: -x[1])
    hotspots = [f"{name}({cnt})" for name, cnt in sorted_by_deps[:5] if cnt >= 3]
    return hotspots


# ── Public API ────────────────────────────────────────────────────────


def load_codebase_memory(*, extra_ctx: dict[str, Any] | None = None) -> CodebaseMemory:
    extra_ctx = extra_ctx or {}
    gitnexus = _read_gitnexus_meta()
    modules = _scan_runtime_modules()
    edges = _build_import_graph(modules)
    ownership = _build_ownership(modules)
    blast_radius = _build_blast_radius(modules, edges)
    risks = _detect_structural_risks(modules, edges, blast_radius)
    hotspots = _detect_hotspots(modules, edges)
    domain_matrix = _build_domain_dependency_matrix(modules, edges)
    score = _compute_score(modules, risks, edges)
    freshness_ts = _now()
    summary = {
        "modules_total": len(modules),
        "edges_total": len(edges),
        "ownership_domains_total": len(ownership),
        "blast_radius_modules_total": len(blast_radius),
        "structural_risks_total": len(risks),
        "hotspots": hotspots,
        "domain_dependencies": domain_matrix,
    }
    det = _hash({
        "modules": sorted(modules.keys()),
        "edges": sorted((e.source, e.target) for e in edges),
        "risks": [(r.risk_type, r.domain) for r in risks],
    })

    freshness = {
        "gitnexus_indexed_at": gitnexus.get("indexedAt", "unknown"),
        "gitnexus_last_commit": gitnexus.get("lastCommit", "unknown")[:12] if gitnexus.get("lastCommit") else "unknown",
        "memory_generated_at": freshness_ts,
    }

    gitnexus_stats = {
        "files": gitnexus.get("stats", {}).get("files", 0),
        "nodes": gitnexus.get("stats", {}).get("nodes", 0),
        "edges": gitnexus.get("stats", {}).get("edges", 0),
        "communities": gitnexus.get("stats", {}).get("communities", 0),
        "processes": gitnexus.get("stats", {}).get("processes", 0),
        "indexed_at": gitnexus.get("indexedAt", "unknown"),
        "last_commit": gitnexus.get("lastCommit", "unknown")[:12] if gitnexus.get("lastCommit") else "unknown",
    }

    return CodebaseMemory(
        contract_version=CODEBASE_CONTRACT_VERSION,
        modules=[m.to_dict() for m in modules.values()],
        dependency_edges=[e.to_dict() for e in edges],
        ownership=[o.to_dict() for o in ownership],
        blast_radius=[b.to_dict() for b in blast_radius],
        structural_risks=[r.to_dict() for r in risks],
        summary=summary,
        score=score,
        determinant_signature=det,
        freshness=freshness,
        gitnexus_stats=gitnexus_stats,
        generated_at=freshness_ts,
    )


def build_codebase_dependency_graph(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "edges": mem.dependency_edges,
        "modules": [m["module_name"] for m in mem.modules],
        "edges_total": len(mem.dependency_edges),
        "modules_total": len(mem.modules),
        "determinant_signature": _hash({"edges": mem.dependency_edges, "modules": [m["module_name"] for m in mem.modules]}),
    }


def build_codebase_module_topology(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    domain_map: dict[str, list[str]] = {}
    for m in mem.modules:
        d = m.get("domain", "other")
        if d not in domain_map:
            domain_map[d] = []
        domain_map[d].append(m.get("module_name", ""))
    return CodebaseTopology(
        modules_total=len(mem.modules),
        domains_total=len(domain_map),
        edges_total=len(mem.dependency_edges),
        hotspots=mem.summary.get("hotspots", []),
        domain_dependency_matrix=mem.summary.get("domain_dependencies", {}),
    ).to_dict()


def build_codebase_ownership(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "domains": mem.ownership,
        "domains_total": len(mem.ownership),
        "determinant_signature": _hash({"ownership": mem.ownership}),
    }


def build_codebase_blast_radius_analysis(
    module_path: str | None = None,
    *,
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    results = mem.blast_radius
    if module_path:
        results = [r for r in results if module_path in r.get("module_path", "")]
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "results": results,
        "results_total": len(results),
        "module_filter": module_path,
        "determinant_signature": _hash({"blast_radius": results}),
    }


def build_codebase_structural_risks(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "risks": mem.structural_risks,
        "risks_total": len(mem.structural_risks),
        "score": mem.score,
        "determinant_signature": _hash({"risks": mem.structural_risks, "score": mem.score}),
    }


def build_codebase_summary(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "summary": mem.summary,
        "score": mem.score,
        "freshness": mem.freshness,
        "gitnexus_stats": mem.gitnexus_stats,
        "determinant_signature": mem.determinant_signature,
    }


def build_codebase_score(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "score": mem.score,
        "determinant_signature": _hash({"score": mem.score}),
    }


def get_codebase_memory_freshness(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    mem = _get_cached("dev36x:memory", lambda: load_codebase_memory(extra_ctx=extra_ctx))
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "freshness": mem.freshness,
        "generated_at": mem.generated_at,
    }


def get_codebase_cache_state() -> dict[str, Any]:
    with _CACHE_LOCK:
        entries = len(_CACHE)
    return {
        "contract_version": CODEBASE_CONTRACT_VERSION,
        "cache_entries": entries,
        "cache_hits": _CACHE_HITS,
        "cache_misses": _CACHE_MISSES,
    }


def reset_codebase_memory_cache() -> None:
    global _CACHE_HITS, _CACHE_MISSES
    with _CACHE_LOCK:
        _CACHE.clear()
        _CACHE_HITS = 0
        _CACHE_MISSES = 0
