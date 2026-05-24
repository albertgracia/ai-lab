"""CRITICAL-PATH-ANALYSIS-01 (FASE 37C)

Hybrid critical-path analysis, bounded + deterministic:
- Primary view: file-level (runtime/*.py)
- Secondary view: domain-level aggregation (runtime/<folder>/)

Read-only, metadata-only, fail-safe.
No routing mutation. No remediation. No runtime/state writes.
"""

from __future__ import annotations

import ast
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any


CRITICAL_PATH_CONTRACT_VERSION = "37C-CRITICAL-PATH-ANALYSIS-01"

_CACHE_LOCK = Lock()
_CACHE: dict[str, Any] | None = None
_CACHE_TS = 0.0
_CACHE_TTL_S = 30.0

_GRAPH_LOCK = Lock()
_FILE_GRAPH_CACHE: dict[str, Any] | None = None
_FILE_GRAPH_TS = 0.0
_FILE_GRAPH_TTL_S = 60.0

_MAX_SCAN_FILES = 450
_MAX_EDGES = 4000
_MAX_DANGEROUS_DEPS = 25


def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _severity_from_score(score: float) -> str:
    s = float(score)
    if s < 0.25:
        return "INFO"
    if s < 0.50:
        return "LOW"
    if s < 0.70:
        return "MEDIUM"
    if s < 0.85:
        return "HIGH"
    return "CRITICAL"


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return int(default)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)


def _triage_severity(summary: dict[str, Any] | None) -> str:
    if not summary:
        return "info"
    if _safe_int(summary.get("total_critical"), 0) > 0:
        return "critical"
    if _safe_int(summary.get("total_high"), 0) > 0:
        return "high"
    if _safe_int(summary.get("total_warning"), 0) > 0:
        return "warning"
    return "info"


def _slo_weight(status: str) -> float:
    v = str(status or "").lower()
    return {
        "healthy": 0.00,
        "warning": 0.10,
        "degraded": 0.25,
        "critical": 0.45,
    }.get(v, 0.15 if v else 0.15)


def _guard_weight(state: str) -> float:
    v = str(state or "").lower()
    return {
        "normal": 0.00,
        "degraded": 0.10,
        "constrained": 0.25,
        "safe_mode": 0.45,
    }.get(v, 0.10 if v else 0.10)


def _severity_weight(sev: str) -> float:
    v = str(sev or "").lower()
    return {
        "info": 0.0,
        "warning": 0.10,
        "high": 0.25,
        "critical": 0.45,
    }.get(v, 0.0)


def _br_weight(br: str) -> float:
    v = str(br or "").lower()
    return {"low": 0.05, "medium": 0.15, "high": 0.30, "critical": 0.45}.get(v, 0.0)


def _gov_weight(risk: str) -> float:
    v = str(risk or "").lower()
    return {"low": 0.05, "medium": 0.12, "high": 0.25, "critical": 0.40}.get(v, 0.0)


def _runtime_root() -> Path:
    return Path("/opt/ai-lab/runtime")


def _is_excluded_path(p: Path) -> bool:
    s = str(p)
    if "/runtime/state/" in s:
        return True
    if "__pycache__" in s:
        return True
    return False


def _parse_runtime_import_targets(py_file: Path) -> list[str]:
    """Return runtime.* import targets (module strings)."""
    try:
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src)
    except Exception:
        return []
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("runtime."):
                    targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.startswith("runtime."):
                targets.append(node.module)
    return targets


def _runtime_module_to_file(mod: str) -> str | None:
    # runtime.foo.bar -> runtime/foo/bar.py
    parts = str(mod).split(".")
    if len(parts) < 3:
        return None
    if parts[0] != "runtime":
        return None
    rel = Path("runtime")
    for seg in parts[1:]:
        rel = rel / seg
    rel_py = str(rel) + ".py"
    abs_path = Path("/opt/ai-lab") / rel_py
    if abs_path.exists():
        return rel_py
    # allow package __init__ fallback
    abs_init = Path("/opt/ai-lab") / str(rel) / "__init__.py"
    if abs_init.exists():
        return str(rel / "__init__.py")
    return None


@dataclass
class DangerousDependency:
    source_file: str
    target_file: str
    relation_type: str
    confidence: float
    direction: str
    reason: str
    affected_plane: str
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "relation_type": self.relation_type,
            "confidence": round(float(self.confidence), 3),
            "direction": self.direction,
            "reason": self.reason,
            "affected_plane": self.affected_plane,
            "severity": self.severity,
        }


@dataclass
class CriticalPathFile:
    file_path: str
    domain: str
    fan_in: int
    fan_out: int
    centrality: float
    blast_radius: str
    governance_risk: str
    runtime_signals: dict[str, Any]
    hard_facts: list[str]
    inferred: list[str]
    unknowns: list[str]
    unavailable_fields: list[str]
    dangerous_dependencies: list[DangerousDependency]
    module_dependency_summary: list[dict[str, Any]]
    score: float
    severity: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "domain": self.domain,
            "fan_in": int(self.fan_in),
            "fan_out": int(self.fan_out),
            "centrality": round(float(self.centrality), 4),
            "blast_radius": self.blast_radius,
            "governance_risk": self.governance_risk,
            "runtime_signals": self.runtime_signals,
            "hard_facts": list(self.hard_facts),
            "inferred": list(self.inferred),
            "unknowns": sorted(set(self.unknowns)),
            "unavailable_fields": sorted(set(self.unavailable_fields)),
            "dangerous_dependencies": [d.to_dict() for d in self.dangerous_dependencies],
            "module_dependency_summary": self.module_dependency_summary,
            "score": round(float(self.score), 3),
            "severity": self.severity,
        }


def reset_critical_path_state() -> dict[str, Any]:
    global _CACHE, _CACHE_TS, _FILE_GRAPH_CACHE, _FILE_GRAPH_TS
    with _CACHE_LOCK:
        _CACHE = None
        _CACHE_TS = 0.0
    with _GRAPH_LOCK:
        _FILE_GRAPH_CACHE = None
        _FILE_GRAPH_TS = 0.0
    return {"reset": True, "timestamp": _now(), "contract_version": CRITICAL_PATH_CONTRACT_VERSION}


def _read_health() -> dict[str, Any] | None:
    try:
        from runtime.health.cognitive_health_layer import build_cognitive_health_snapshot
        return build_cognitive_health_snapshot(window_minutes=60)
    except Exception:
        return None


def _read_slo() -> dict[str, Any] | None:
    try:
        from runtime.slo.cognitive_slo import get_slo_status
        return get_slo_status()
    except Exception:
        return None


def _read_triage() -> dict[str, Any] | None:
    try:
        from runtime.triage.autonomous_triage import get_triage_summary
        return get_triage_summary()
    except Exception:
        return None


def _read_guard() -> dict[str, Any] | None:
    try:
        from runtime.federation.federation_guards import get_federation_guard_summary
        return get_federation_guard_summary()
    except Exception:
        return None


def _read_evidence() -> dict[str, Any] | None:
    try:
        from runtime.federation.federation_observability import get_evidence_summary
        return get_evidence_summary()
    except Exception:
        return None


def _read_architecture() -> dict[str, Any] | None:
    try:
        from runtime.governance.architecture_governance import get_architecture_summary
        return get_architecture_summary()
    except Exception:
        return None


def _read_graph_hotspots() -> dict[str, Any] | None:
    try:
        from runtime.graph_reasoning.gitnexus_graph_reasoning import get_graph_hotspots
        return get_graph_hotspots()
    except Exception:
        return None


def _file_domain(file_path: str) -> str:
    p = str(file_path)
    if p.startswith("runtime/"):
        parts = p.split("/")
        if len(parts) >= 2:
            return parts[1]
    return "other"


def _build_file_import_graph(
    *,
    runtime_only: bool = True,
    include_apps: bool = False,
) -> dict[str, Any]:
    """Return bounded file-level import graph for runtime/*.py.

    Output:
    - files: set[str]
    - edges: list[tuple[str,str]]  (source_file -> target_file)
    - fan_in/out maps
    """
    global _FILE_GRAPH_CACHE, _FILE_GRAPH_TS
    now = _now()
    with _GRAPH_LOCK:
        if _FILE_GRAPH_CACHE and (now - float(_FILE_GRAPH_TS)) <= _FILE_GRAPH_TTL_S:
            return dict(_FILE_GRAPH_CACHE)

    root = _runtime_root()
    all_py = [p for p in root.rglob("*.py") if p.is_file() and not _is_excluded_path(p)]

    # Deterministic order
    all_py = sorted(all_py, key=lambda p: str(p))

    # Always include known critical files if present
    critical_files = [
        "runtime/gateway/openai_gateway.py",
        "runtime/gateway/runtime_api_routes.py",
        "runtime/federation/federation_guards.py",
        "runtime/federation/role_router.py",
        "runtime/health/cognitive_health_layer.py",
        "runtime/correlation/graph_runtime_correlation.py",
        "runtime/slo/cognitive_slo.py",
        "runtime/triage/autonomous_triage.py",
        "runtime/graph_reasoning/gitnexus_graph_reasoning.py",
        "runtime/telemetry/prometheus_metrics.py",
        "runtime/models/model_registry.py",
    ]

    selected: list[Path] = []
    selected_set: set[str] = set()

    for rel in critical_files:
        abs_p = Path("/opt/ai-lab") / rel
        if abs_p.exists():
            selected.append(abs_p)
            selected_set.add(str(abs_p))

    for p in all_py:
        if len(selected) >= _MAX_SCAN_FILES:
            break
        if str(p) in selected_set:
            continue
        selected.append(p)
        selected_set.add(str(p))

    # Build file set and edges
    files: set[str] = set()
    edges: list[tuple[str, str]] = []
    for p in selected:
        rel = str(p.relative_to(Path("/opt/ai-lab")))
        if runtime_only and not rel.startswith("runtime/"):
            continue
        files.add(rel)

    for p in selected:
        src_rel = str(p.relative_to(Path("/opt/ai-lab")))
        if src_rel not in files:
            continue
        for imp in _parse_runtime_import_targets(p):
            tgt = _runtime_module_to_file(imp)
            if not tgt:
                continue
            if runtime_only and not tgt.startswith("runtime/"):
                continue
            if "/runtime/state/" in ("/" + tgt + "/"):
                continue
            if tgt not in files:
                # only include edges to in-scope files
                continue
            edges.append((src_rel, tgt))
            if len(edges) >= _MAX_EDGES:
                break
        if len(edges) >= _MAX_EDGES:
            break

    # fan-in/out
    out_map: dict[str, set[str]] = defaultdict(set)
    in_map: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        out_map[a].add(b)
        in_map[b].add(a)

    fan_in = {f: len(in_map.get(f, set())) for f in files}
    fan_out = {f: len(out_map.get(f, set())) for f in files}
    max_fi = max(fan_in.values()) if fan_in else 1
    max_fo = max(fan_out.values()) if fan_out else 1
    centrality = {f: round((fan_in.get(f, 0) / max_fi * 0.6 + fan_out.get(f, 0) / max_fo * 0.4), 6) for f in files}

    payload = {
        "files": sorted(files),
        "edges": edges,
        "fan_in": fan_in,
        "fan_out": fan_out,
        "centrality": centrality,
        "max_fan_in": max_fi,
        "max_fan_out": max_fo,
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
    }

    with _GRAPH_LOCK:
        _FILE_GRAPH_CACHE = dict(payload)
        _FILE_GRAPH_TS = now
    return payload


def _classify_blast_radius_from_impacted(total_impacted: int) -> str:
    if total_impacted <= 1:
        return "low"
    if total_impacted <= 4:
        return "medium"
    if total_impacted <= 10:
        return "high"
    return "critical"


def _blast_radius_for_file(file_path: str, out_map: dict[str, set[str]]) -> tuple[str, int]:
    # bounded BFS depth 3
    visited: set[str] = {file_path}
    q: deque[tuple[str, int]] = deque([(file_path, 0)])
    impacted: set[str] = set()
    while q:
        cur, depth = q.popleft()
        if depth >= 3:
            continue
        for dep in sorted(out_map.get(cur, set())):
            if dep in visited:
                continue
            visited.add(dep)
            impacted.add(dep)
            q.append((dep, depth + 1))
            if len(impacted) >= 50:
                break
        if len(impacted) >= 50:
            break
    return _classify_blast_radius_from_impacted(len(impacted)), len(impacted)


def _governance_risk_for_file(file_path: str, arch: dict[str, Any] | None) -> str:
    # Use architecture hotspots/violations if module matches; else fallback to centrality-based later.
    if not arch or not isinstance(arch, dict):
        return "unknown"
    hs = arch.get("hotspots", []) or []
    viol = arch.get("governance_violations", []) or []
    domain = _file_domain(file_path)
    # If any hotspot module equals domain name, treat elevated.
    if any(isinstance(x, dict) and str(x.get("module") or "") == domain for x in hs):
        return "high"
    if any(isinstance(x, dict) and str(x.get("module") or "") == domain for x in viol):
        return "critical"
    return "low"


def _signals_bundle() -> tuple[dict[str, Any], list[str], list[str], list[str]]:
    hard: list[str] = []
    unknowns: list[str] = []
    unavailable: list[str] = []

    health = _read_health()
    slo = _read_slo()
    triage = _read_triage()
    guard = _read_guard()
    evidence = _read_evidence()
    arch = _read_architecture()
    graph_hotspots = _read_graph_hotspots()

    if health is None:
        unavailable.append("cognitive_health")
        unknowns.append("cognitive_health_unavailable")
    else:
        hard.append("cognitive_health")

    if slo is None:
        unavailable.append("slo_status")
        unknowns.append("slo_unavailable")
    else:
        hard.append("slo_status")

    if triage is None:
        unavailable.append("triage_summary")
        unknowns.append("triage_unavailable")
    else:
        hard.append("triage_summary")

    if guard is None:
        unavailable.append("federation_guard")
        unknowns.append("federation_guard_unavailable")
    else:
        hard.append("federation_guard")

    if evidence is None:
        unavailable.append("evidence_summary")
        unknowns.append("evidence_unavailable")
    else:
        hard.append("evidence_summary")

    if arch is None:
        unavailable.append("architecture_summary")
        unknowns.append("architecture_unavailable")
    else:
        hard.append("architecture_summary")

    if graph_hotspots is None:
        unavailable.append("graph_hotspots")
        unknowns.append("graph_hotspots_unavailable")
    else:
        hard.append("graph_hotspots")

    bundle = {
        "health": health or {},
        "slo": slo or {},
        "triage": triage or {},
        "guard": guard or {},
        "evidence": evidence or {},
        "arch": arch or {},
        "graph_hotspots": graph_hotspots or {},
    }
    return bundle, hard, unknowns, unavailable


def _runtime_health_numbers(health: dict[str, Any]) -> tuple[float, float]:
    hs = _safe_float(health.get("score"), 0.0)
    rc = _safe_float((health.get("routing_confidence") or {}).get("confidence"), 0.0)
    return hs, rc


def _guard_state(guard: dict[str, Any]) -> str:
    st = guard.get("state")
    if isinstance(st, dict):
        return str(st.get("state") or "unknown")
    return str(st or "unknown")


def _evidence_counters(evidence: dict[str, Any]) -> dict[str, int]:
    return {
        "replay_risk_total": _safe_int(evidence.get("replay_risk_total"), 0),
        "stale_evidence_total": _safe_int(evidence.get("stale_evidence_total"), 0),
        "invalid_lineage_total": _safe_int(evidence.get("invalid_lineage_total"), 0),
        "lineage_depth_max": _safe_int(evidence.get("lineage_depth_max"), 0),
    }


def _score_file(
    *,
    centrality: float,
    fan_in: int,
    fan_out: int,
    blast_radius: str,
    governance_risk: str,
    health_score: float,
    routing_confidence: float,
    slo_status: str,
    triage_sev: str,
    guard_state: str,
    evidence: dict[str, int],
    missing_sources: int,
) -> float:
    graph = _clamp01(0.60 * _clamp01(centrality) + 0.20 * _clamp01(min(1.0, fan_in / 30.0)) + 0.20 * _clamp01(min(1.0, fan_out / 30.0)))
    graph += _br_weight(blast_radius) + _gov_weight(governance_risk)

    hs_norm = _clamp01(1.0 - (health_score / 100.0))
    rc_norm = _clamp01(1.0 - routing_confidence)
    runtime = 0.45 * hs_norm + 0.25 * rc_norm + _slo_weight(slo_status) + _severity_weight(triage_sev) + _guard_weight(guard_state)

    ev = _clamp01(min(1.0, evidence.get("replay_risk_total", 0) / 10.0) * 0.5 + min(1.0, evidence.get("stale_evidence_total", 0) / 10.0) * 0.25 + min(1.0, evidence.get("invalid_lineage_total", 0) / 5.0) * 0.25)

    score = 0.45 * _clamp01(graph) + 0.45 * _clamp01(runtime) + 0.10 * ev
    penalty = 0.05 * min(6, int(missing_sources))
    return _clamp01(score - penalty)


def _dangerous_deps_for_file(
    file_path: str,
    out_map: dict[str, set[str]],
    in_map: dict[str, set[str]],
) -> tuple[list[DangerousDependency], list[dict[str, Any]]]:
    deps: list[DangerousDependency] = []
    domain_edges: dict[tuple[str, str], int] = defaultdict(int)

    src_dom = _file_domain(file_path)

    # Outbound
    for tgt in sorted(out_map.get(file_path, set()))[:50]:
        tgt_dom = _file_domain(tgt)
        domain_edges[(src_dom, tgt_dom)] += 1
        sev = "medium" if src_dom != tgt_dom else "low"
        deps.append(DangerousDependency(
            source_file=file_path,
            target_file=tgt,
            relation_type="import",
            confidence=1.0,
            direction="outbound",
            reason="runtime_import",
            affected_plane="runtime",
            severity=sev.upper(),
        ))

    # Inbound
    for src in sorted(in_map.get(file_path, set()))[:50]:
        sdom = _file_domain(src)
        domain_edges[(sdom, src_dom)] += 1
        sev = "high" if sdom != src_dom else "medium"
        deps.append(DangerousDependency(
            source_file=src,
            target_file=file_path,
            relation_type="import",
            confidence=1.0,
            direction="inbound",
            reason="runtime_import",
            affected_plane="runtime",
            severity=sev.upper(),
        ))

    # deterministic + bounded
    deps.sort(key=lambda d: (d.severity, d.direction, d.source_file, d.target_file))
    deps = deps[:_MAX_DANGEROUS_DEPS]

    # Module dependency summary
    summaries: list[dict[str, Any]] = []
    for (a, b), cnt in sorted(domain_edges.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))[:20]:
        highest = "HIGH" if a != b else "MEDIUM" if cnt >= 3 else "LOW"
        summaries.append({
            "source_domain": a,
            "target_domain": b,
            "edges_total": int(cnt),
            "highest_severity": highest,
            "risk_reason": "cross_domain_import" if a != b else "intra_domain_import",
        })

    return deps, summaries


def build_critical_path_snapshot(*, top_n: int = 10, runtime_only: bool = True, include_apps: bool = False) -> dict[str, Any]:
    """Return critical path snapshot.

    - top_n default 10, cap 25
    - always includes all HIGH/CRITICAL even if outside top_n
    """
    lim = max(1, min(25, int(top_n)))

    bundle, hard_facts, unknowns, unavailable_fields = _signals_bundle()
    health = bundle["health"]
    slo = bundle["slo"]
    triage = bundle["triage"]
    guard = bundle["guard"]
    evidence = bundle["evidence"]
    arch = bundle["arch"]

    hs, rc = _runtime_health_numbers(health)
    slo_status = str(slo.get("overall_status") or "unknown")
    triage_sev = _triage_severity(triage)
    guard_state = _guard_state(guard)
    ev = _evidence_counters(evidence)

    graph = _build_file_import_graph(runtime_only=runtime_only, include_apps=include_apps)
    files = graph.get("files", []) or []
    edges = graph.get("edges", []) or []
    fin = graph.get("fan_in", {}) or {}
    fout = graph.get("fan_out", {}) or {}
    cent = graph.get("centrality", {}) or {}

    out_map: dict[str, set[str]] = defaultdict(set)
    in_map: dict[str, set[str]] = defaultdict(set)
    for a, b in edges:
        out_map[a].add(b)
        in_map[b].add(a)

    results: list[CriticalPathFile] = []
    missing_sources = len(unavailable_fields)

    for f in files:
        if not str(f).startswith("runtime/"):
            continue
        if str(f).startswith("runtime/state/"):
            continue

        domain = _file_domain(f)
        fi = _safe_int(fin.get(f), 0)
        fo = _safe_int(fout.get(f), 0)
        c = _safe_float(cent.get(f), 0.0)
        br, impacted = _blast_radius_for_file(f, out_map)
        gr = _governance_risk_for_file(f, arch)

        hard: list[str] = ["import_graph"]
        inf: list[str] = []
        unk: list[str] = []
        unavail: list[str] = []

        if unavailable_fields:
            unavail.extend(unavailable_fields)
            unk.append("partial_sources")

        if br in {"high", "critical"}:
            inf.append("wide_blast_radius")
        if gr in {"high", "critical"}:
            inf.append("elevated_governance_risk")
        if rc and rc < 0.70:
            inf.append("routing_confidence_degraded")
        if str(slo_status).lower() in {"degraded", "critical"}:
            inf.append("slo_not_healthy")
        if triage_sev in {"warning", "high", "critical"}:
            inf.append("triage_active")
        if str(guard_state).lower() in {"constrained", "safe_mode"}:
            inf.append("federation_guard_elevated")

        deps, dep_summary = _dangerous_deps_for_file(f, out_map, in_map)

        score = _score_file(
            centrality=c,
            fan_in=fi,
            fan_out=fo,
            blast_radius=br,
            governance_risk=gr,
            health_score=hs,
            routing_confidence=rc,
            slo_status=slo_status,
            triage_sev=triage_sev,
            guard_state=guard_state,
            evidence=ev,
            missing_sources=missing_sources,
        )
        sev = _severity_from_score(score)

        runtime_signals = {
            "health_score": round(float(hs), 1),
            "routing_confidence": round(float(rc), 3),
            "slo_status": slo_status,
            "triage_severity": triage_sev,
            "federation_guard_state": guard_state,
            "evidence": dict(ev),
        }

        results.append(CriticalPathFile(
            file_path=f,
            domain=domain,
            fan_in=fi,
            fan_out=fo,
            centrality=c,
            blast_radius=br,
            governance_risk=gr,
            runtime_signals=runtime_signals,
            hard_facts=hard,
            inferred=inf,
            unknowns=unk,
            unavailable_fields=unavail,
            dangerous_dependencies=deps,
            module_dependency_summary=dep_summary,
            score=score,
            severity=sev,
        ))

    results.sort(key=lambda r: (-r.score, r.file_path))

    top = results[:lim]
    extra = [r for r in results[lim:] if r.severity in {"HIGH", "CRITICAL"}]
    # include all HIGH/CRITICAL regardless of top_n, bounded to keep payload safe
    extra = extra[:25]

    # domain aggregation
    domain_map: dict[str, list[CriticalPathFile]] = defaultdict(list)
    for r in results:
        domain_map[r.domain].append(r)
    domain_summary = []
    for dom in sorted(domain_map.keys()):
        items = domain_map[dom]
        avg = sum(i.score for i in items) / max(len(items), 1)
        mx = max(i.score for i in items) if items else 0.0
        high = sum(1 for i in items if i.severity in {"HIGH", "CRITICAL"})
        domain_summary.append({
            "domain": dom,
            "files_total": len(items),
            "avg_score": round(float(avg), 3),
            "max_score": round(float(mx), 3),
            "high_critical_total": int(high),
        })
    domain_summary.sort(key=lambda d: (-float(d.get("max_score", 0)), d.get("domain", "")))

    # global score: top file score adjusted by runtime degradation
    runtime_deg = _clamp01((1.0 - hs / 100.0) * 0.6 + (1.0 - rc) * 0.4)
    global_score = _clamp01((top[0].score if top else 0.0) * 0.75 + runtime_deg * 0.25)
    global_sev = _severity_from_score(global_score)

    recs = _build_recommendations(global_sev, rc, slo_status, guard_state, unavailable_fields)

    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "scope": "runtime_only" if runtime_only else "full",
        "top_n": int(lim),
        "score": round(float(global_score), 3),
        "severity": global_sev,
        "top_files": [t.to_dict() for t in top],
        "high_critical_outside_top": [e.to_dict() for e in extra],
        "domain_summary": domain_summary[:25],
        "unknowns": sorted(set(unknowns)),
        "unavailable_fields": sorted(set(unavailable_fields)),
        "hard_facts": hard_facts,
        "recommendations": recs,
    }


def _build_recommendations(severity: str, routing_confidence: float, slo_status: str, guard_state: str, unavailable_fields: list[str]) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    if unavailable_fields:
        recs.append({
            "severity": "LOW",
            "recommendation": "Fill missing sources before acting on critical-path",
            "rationale": f"missing_sources={sorted(set(unavailable_fields))}",
            "confidence": "low",
        })
    if routing_confidence and routing_confidence < 0.70:
        recs.append({
            "severity": "MEDIUM",
            "recommendation": "Routing confidence degraded (single-node/low avg score); prefer low-risk changes",
            "rationale": f"routing_confidence={round(float(routing_confidence),3)}",
            "confidence": "medium",
        })
    if str(slo_status).lower() in {"degraded", "critical"}:
        recs.append({
            "severity": "HIGH",
            "recommendation": "Treat SLO degradation as primary; use critical-path to narrow suspects",
            "rationale": f"slo_status={slo_status}",
            "confidence": "high",
        })
    if str(guard_state).lower() in {"constrained", "safe_mode"}:
        recs.append({
            "severity": "HIGH",
            "recommendation": "Investigate federation guard state + evidence counters before refactors",
            "rationale": f"guard_state={guard_state}",
            "confidence": "high",
        })
    if not recs:
        recs.append({
            "severity": "INFO",
            "recommendation": "No immediate critical-path action",
            "rationale": f"severity={severity}",
            "confidence": "medium",
        })
    recs = recs[:8]
    recs.sort(key=lambda r: (r.get("severity", ""), r.get("recommendation", "")))
    return recs


def _get_cached_snapshot(top_n: int = 10) -> dict[str, Any]:
    global _CACHE, _CACHE_TS
    now = _now()
    with _CACHE_LOCK:
        if _CACHE and (now - float(_CACHE_TS)) <= _CACHE_TTL_S:
            # top_n impacts payload size; do not reuse if top_n differs
            if int(_CACHE.get("top_n", 10)) == int(max(1, min(25, int(top_n)))):
                return dict(_CACHE)
    snap = build_critical_path_snapshot(top_n=top_n)
    with _CACHE_LOCK:
        _CACHE = dict(snap)
        _CACHE_TS = now
    return snap


def get_critical_path_summary() -> dict[str, Any]:
    snap = _get_cached_snapshot(top_n=10)
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path/summary",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "score": snap.get("score", 0.0),
        "severity": snap.get("severity", "INFO"),
        "top_n": snap.get("top_n", 10),
        "unknowns": snap.get("unknowns", []),
        "unavailable_fields": snap.get("unavailable_fields", []),
        "recommendations_total": len(snap.get("recommendations", []) or []),
    }


def get_critical_path_modules(*, top_n: int = 10) -> dict[str, Any]:
    snap = _get_cached_snapshot(top_n=top_n)
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path/modules",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "top_files": snap.get("top_files", []),
        "high_critical_outside_top": snap.get("high_critical_outside_top", []),
        "domain_summary": snap.get("domain_summary", []),
        "top_n": snap.get("top_n", 10),
    }


def get_critical_path_routes() -> dict[str, Any]:
    # deterministic route map
    routes = [
        {"route": "/metrics", "linked_domains": ["telemetry", "gateway"], "plane": "observability"},
        {"route": "/health", "linked_domains": ["gateway"], "plane": "runtime_api"},
        {"route": "/runtime/health", "linked_domains": ["health", "telemetry", "control"], "plane": "runtime_api"},
        {"route": "/runtime/correlation", "linked_domains": ["correlation", "graph_reasoning", "health", "slo", "triage", "federation", "governance"], "plane": "runtime_api"},
        {"route": "/runtime/graph", "linked_domains": ["graph_reasoning", "codebase", "governance", "federation", "slo", "triage"], "plane": "runtime_api"},
        {"route": "/runtime/slo/status", "linked_domains": ["slo"], "plane": "runtime_api"},
        {"route": "/runtime/triage/summary", "linked_domains": ["triage"], "plane": "runtime_api"},
        {"route": "/v1/chat/completions", "linked_domains": ["gateway", "router", "models"], "plane": "inference"},
    ]
    # Score per route from current domain_summary
    snap = _get_cached_snapshot(top_n=10)
    dom = {d.get("domain"): float(d.get("max_score", 0) or 0) for d in (snap.get("domain_summary", []) or []) if isinstance(d, dict)}
    out = []
    for r in routes:
        mx = 0.0
        for d in r.get("linked_domains", []):
            mx = max(mx, float(dom.get(d, 0.0)))
        score = _clamp01(mx)
        out.append({
            "route": r["route"],
            "plane": r["plane"],
            "linked_domains": r["linked_domains"],
            "score": round(float(score), 3),
            "severity": _severity_from_score(score),
        })
    out.sort(key=lambda x: (-float(x.get("score", 0)), x.get("route", "")))
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path/routes",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "routes": out,
        "total": len(out),
    }


def get_critical_path_dependencies(*, file_path: str) -> dict[str, Any]:
    # bounded lookup: build graph and return edges touching file
    graph = _build_file_import_graph(runtime_only=True)
    edges = graph.get("edges", []) or []
    f = str(file_path or "")
    if not f.startswith("runtime/"):
        f = "runtime/" + f.lstrip("/")
    related = []
    for a, b in edges:
        if a == f or b == f:
            related.append({"source_file": a, "target_file": b, "relation_type": "import", "confidence": 1.0})
        if len(related) >= 100:
            break
    related.sort(key=lambda x: (x.get("source_file", ""), x.get("target_file", "")))
    return {
        "status": "ok",
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path/dependencies",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "file_path": f,
        "edges": related,
        "edges_total": len(related),
        "unknowns": [] if related else ["no_edges_or_file_out_of_scope"],
    }


def get_critical_path_recommendations() -> dict[str, Any]:
    snap = _get_cached_snapshot(top_n=10)
    recs = snap.get("recommendations", []) or []
    return {
        "status": snap.get("status", "ok"),
        "service": "ai-lab-openai-gateway",
        "endpoint": "runtime/critical-path/recommendations",
        "timestamp": _now(),
        "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
        "recommendations": recs,
        "total": len(recs),
    }


def build_critical_path_prometheus_metrics() -> str:
    """Render critical path metrics as Prometheus text (fail-safe)."""
    try:
        snap = _get_cached_snapshot(top_n=10)
        score = float(snap.get("score", 0) or 0)
        top_files = snap.get("top_files", []) or []
        high_out = snap.get("high_critical_outside_top", []) or []
        high_total = sum(1 for f in (top_files + high_out) if isinstance(f, dict) and f.get("severity") in {"HIGH", "CRITICAL"})
        critical_total = sum(1 for f in (top_files + high_out) if isinstance(f, dict) and f.get("severity") == "CRITICAL")
        unknowns_total = float(len(snap.get("unknowns", []) or []) + len(snap.get("unavailable_fields", []) or []))
        recs_total = float(len(snap.get("recommendations", []) or []))
        routes = get_critical_path_routes().get("routes", []) or []
        routes_critical = sum(1 for r in routes if isinstance(r, dict) and r.get("severity") in {"HIGH", "CRITICAL"})
        return (
            f"ailab_critical_path_score {score}\n"
            f"ailab_critical_path_top_modules_total {float(len(top_files))}\n"
            f"ailab_critical_path_high_total {float(high_total)}\n"
            f"ailab_critical_path_critical_total {float(critical_total)}\n"
            f"ailab_critical_path_unknowns_total {unknowns_total}\n"
            f"ailab_critical_path_routes_critical_total {float(routes_critical)}\n"
            f"ailab_critical_path_recommendations_total {recs_total}\n"
        )
    except Exception:
        return (
            "ailab_critical_path_score 0\n"
            "ailab_critical_path_top_modules_total 0\n"
            "ailab_critical_path_high_total 0\n"
            "ailab_critical_path_critical_total 0\n"
            "ailab_critical_path_unknowns_total 0\n"
            "ailab_critical_path_routes_critical_total 0\n"
            "ailab_critical_path_recommendations_total 0\n"
        )
