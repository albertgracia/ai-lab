"""GITNEXUS-ARCHITECTURE-GOVERNANCE-01: bounded architecture governance framework.

Purpose: detect architectural drift, identify gravity centers, measure coupling,
and define structural budgets for AI-LAB runtime. Uses filesystem-level static
analysis (bounded, deterministic) with optional GitNexus enrichment.

Hard rules:
- No persistence, no databases, no background threads.
- No runtime behavior changes; governance only observes, scores, and exposes.
- Bounded scanning: max depth, max files, max results.
- Fail-safe: GitNexus unavailable -> degrade gracefully.
"""

from __future__ import annotations

import ast
import os
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Any


ARCHITECTURE_CONTRACT_VERSION = "ARCH-01"

# Runtime root for static analysis
_RUNTIME_ROOT = Path("/opt/ai-lab/runtime")
_GATEWAY_ROOT = Path("/opt/ai-lab/runtime/gateway")

# Bounded scan limits
_MAX_FILES = 300
_MAX_DEPTH = 8
_MAX_RESULTS = 50

# Governance policies (declarative thresholds)

GOVERNANCE_POLICIES: list[dict[str, Any]] = [
    {
        "id": "GOV-ARCH-001",
        "name": "gateway_must_not_import_routing_execution",
        "description": "Gateway must not directly import routing execution modules",
        "target_pattern": "runtime/gateway",
        "forbidden_imports": ["runtime.llm", "runtime.router", "runtime.executor", "runtime.planner"],
        "severity": "critical",
    },
    {
        "id": "GOV-ARCH-002",
        "name": "registry_must_not_orchestrate_routing",
        "description": "Model registry must not import routing decision modules",
        "target_pattern": "runtime/models",
        "forbidden_imports": ["runtime.llm.router", "runtime.executor", "runtime.planner"],
        "severity": "error",
    },
    {
        "id": "GOV-ARCH-003",
        "name": "observability_must_remain_read_only",
        "description": "Observability modules must not import runtime execution",
        "target_pattern": "runtime/telemetry",
        "forbidden_imports": ["runtime.llm", "runtime.executor", "runtime.planner", "runtime.gateway"],
        "severity": "error",
    },
    {
        "id": "GOV-ARCH-004",
        "name": "federation_must_remain_bounded",
        "description": "Federation must not import gateway or runtime execution",
        "target_pattern": "runtime/federation",
        "forbidden_imports": ["runtime.gateway", "runtime.llm", "runtime.executor", "runtime.planner"],
        "severity": "error",
    },
    {
        "id": "GOV-ARCH-005",
        "name": "no_recursive_governance_loops",
        "description": "Governance must not import runtime execution or gateway",
        "target_pattern": "runtime/governance",
        "forbidden_imports": ["runtime.gateway", "runtime.llm", "runtime.executor", "runtime.planner"],
        "severity": "warning",
    },
    {
        "id": "GOV-ARCH-006",
        "name": "guards_must_not_import_execution",
        "description": "Guard/validation modules must not import runtime execution",
        "target_pattern": "runtime/validation",
        "forbidden_imports": ["runtime.llm", "runtime.executor", "runtime.planner", "runtime.gateway"],
        "severity": "error",
    },
]

# Coupling thresholds
_COUPLING_THRESHOLDS = {
    "fan_in_low": 3,
    "fan_in_medium": 8,
    "fan_in_high": 15,
    "fan_out_low": 3,
    "fan_out_medium": 8,
    "fan_out_high": 15,
    "imports_low": 10,
    "imports_medium": 25,
    "imports_high": 50,
    "calls_low": 5,
    "calls_medium": 15,
    "calls_high": 30,
}


class GovernanceSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class CouplingLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class ModuleDependency:
    source: str
    target: str
    import_type: str = "import"

    def to_dict(self) -> dict[str, Any]:
        return {"source": self.source, "target": self.target, "import_type": self.import_type}


@dataclass(frozen=True)
class ModuleRisk:
    module: str
    imports: int
    fan_in: int
    fan_out: int
    coupling_score: float
    coupling_level: CouplingLevel
    is_gravity_center: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "imports": self.imports,
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "coupling_score": round(self.coupling_score, 4),
            "coupling_level": self.coupling_level.value,
            "is_gravity_center": self.is_gravity_center,
        }


@dataclass(frozen=True)
class GovernanceViolation:
    policy_id: str
    policy_name: str
    module: str
    violation: str
    severity: GovernanceSeverity
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "module": self.module,
            "violation": self.violation,
            "severity": self.severity.value,
            "timestamp": float(self.timestamp),
        }


@dataclass(frozen=True)
class ArchitectureSnapshot:
    contract_version: str
    timestamp: float
    modules_analyzed: int
    total_dependencies: int
    gravity_centers: list[dict[str, Any]]
    high_risk_modules: list[dict[str, Any]]
    coupling_summary: dict[str, Any]
    governance_violations: list[dict[str, Any]]
    hotspots: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "timestamp": float(self.timestamp),
            "modules_analyzed": int(self.modules_analyzed),
            "total_dependencies": int(self.total_dependencies),
            "gravity_centers": list(self.gravity_centers),
            "high_risk_modules": list(self.high_risk_modules),
            "coupling_summary": dict(self.coupling_summary),
            "governance_violations": list(self.governance_violations),
            "hotspots": list(self.hotspots),
        }


# ── In-memory state — bounded, thread-safe ──────────────────────────────

_lock = Lock()

# Cached analysis (bounded TTL: 300s = 5 min)
_cache: dict[str, Any] = {}
_cache_ts: float = 0.0
_CACHE_TTL = 300.0

_violations_store: list[dict[str, Any]] = []
_violations_max = 128


def _now_ts(now: float | None) -> float:
    return float(now) if now is not None else float(time.time())


def _clamp_int(val: Any, *, default: int, lo: int, hi: int) -> int:
    try:
        i = int(val)
        return max(int(lo), min(int(hi), i))
    except Exception:
        return int(default)


def _walk_py_files(root: Path, *, max_files: int, max_depth: int) -> list[Path]:
    """Walk Python files bounded by max_files and max_depth."""
    files: list[Path] = []
    root_str = str(root)
    try:
        for dirpath_str, dirnames, filenames in os.walk(str(root)):
            dirpath = Path(dirpath_str)
            rel = dirpath.relative_to(root).parts
            if len(rel) >= max_depth:
                dirnames.clear()
                continue
            dirnames[:] = [d for d in dirnames if not d.startswith("__") and d != "__pycache__"]
            for fn in filenames:
                if fn.endswith(".py") and fn != "__init__.py":
                    if len(files) >= max_files:
                        dirnames.clear()
                        break
                    files.append(dirpath / fn)
            if len(files) >= max_files:
                break
    except Exception:
        pass
    return files


def _parse_imports(filepath: Path) -> list[str]:
    """Parse imports from a Python file (bounded, fail-safe)."""
    imports: list[str] = []
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(str(alias.name).split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    parts = node.module.split(".")
                    imports.append(parts[0])
                    if len(parts) > 1:
                        imports.append(".".join(parts[:2]))
    except Exception:
        pass
    return list(set(imports))


def _compute_coupling_score(fan_in: int, fan_out: int, imports: int) -> float:
    """Simple coupling heuristic: higher is more coupled/risky."""
    return float(fan_in * 0.4 + fan_out * 0.4 + imports * 0.2)


def _get_coupling_level(score: float) -> CouplingLevel:
    if score < 5:
        return CouplingLevel.LOW
    elif score < 15:
        return CouplingLevel.MEDIUM
    elif score < 30:
        return CouplingLevel.HIGH
    return CouplingLevel.CRITICAL


def _is_runtime_path(module_path: str) -> bool:
    """Check if a module path is within the runtime tree."""
    return module_path.startswith("runtime/") or module_path.startswith("runtime.")


def _module_name_from_path(filepath: Path) -> str:
    """Convert a file path to a dotted module name relative to runtime root."""
    try:
        rel = filepath.relative_to(_RUNTIME_ROOT.parent)
        return str(rel.with_suffix("")).replace("/", ".")
    except Exception:
        return str(filepath)


def _check_policy(policy: dict[str, Any], module_deps: dict[str, set[str]]) -> list[GovernanceViolation]:
    """Check a single governance policy against analyzed dependencies."""
    violations: list[GovernanceViolation] = []
    target_prefix = policy["target_pattern"].replace("/", ".")
    forbidden = policy["forbidden_imports"]
    for module, deps in module_deps.items():
        if not module.startswith(target_prefix):
            continue
        for dep in deps:
            for forbidden_prefix in forbidden:
                if dep.startswith(forbidden_prefix) or dep == forbidden_prefix:
                    violations.append(
                        GovernanceViolation(
                            policy_id=policy["id"],
                            policy_name=policy["name"],
                            module=module,
                            violation=f"imports {dep} (forbidden by {policy['id']})",
                            severity=GovernanceSeverity(policy["severity"]),
                            timestamp=time.time(),
                        )
                    )
                    break
    return violations


# ── Public API ───────────────────────────────────────────────────────────

def reset_architecture_state() -> None:
    """Test helper: reset cached analysis and violations."""
    global _cache, _cache_ts, _violations_store
    with _lock:
        _cache = {}
        _cache_ts = 0.0
        _violations_store.clear()


def analyze_architecture(*, now: float | None = None) -> dict[str, Any]:
    """Run bounded architectural analysis.

    Uses filesystem-level static import analysis. Cached for _CACHE_TTL seconds.
    Always deterministic and bounded.
    """
    global _cache, _cache_ts

    ts = _now_ts(now)

    with _lock:
        if _cache and ts - _cache_ts < _CACHE_TTL:
            return dict(_cache)

    # Scan Python files
    files = _walk_py_files(_RUNTIME_ROOT, max_files=_MAX_FILES, max_depth=_MAX_DEPTH)

    # Parse imports per module
    module_imports: dict[str, set[str]] = {}
    for fp in files:
        mod = _module_name_from_path(fp)
        imps = _parse_imports(fp)
        module_imports[mod] = set(imps)

    # Build dependency map (runtime modules only)
    module_deps: dict[str, set[str]] = {}
    for mod, imps in module_imports.items():
        runtime_deps: set[str] = set()
        for imp in imps:
            if _is_runtime_path(imp):
                runtime_deps.add(imp)
        module_deps[mod] = runtime_deps

    # Compute fan-in / fan-out
    fan_in: Counter[str] = Counter()
    fan_out: Counter[str] = Counter()
    for mod, deps in module_deps.items():
        fan_out[mod] = len(deps)
        for dep in deps:
            fan_in[dep] += 1

    # Module risk scoring (only for modules that are in our scan set)
    module_risks: list[ModuleRisk] = []
    for mod in sorted(module_deps.keys()):
        fi = fan_in.get(mod, 0)
        fo = fan_out.get(mod, 0)
        imps_count = len(module_imports.get(mod, set()))
        score = _compute_coupling_score(fi, fo, imps_count)
        level = _get_coupling_level(score)
        is_gravity = fi >= _COUPLING_THRESHOLDS["fan_in_high"] or fo >= _COUPLING_THRESHOLDS["fan_out_high"]
        module_risks.append(ModuleRisk(
            module=mod,
            imports=imps_count,
            fan_in=fi,
            fan_out=fo,
            coupling_score=score,
            coupling_level=level,
            is_gravity_center=is_gravity,
        ))

    # Gravity centers (high fan-in or high fan-out)
    gravity_centers = sorted(
        [m.to_dict() for m in module_risks if m.is_gravity_center],
        key=lambda x: -x["coupling_score"],
    )[:_MAX_RESULTS]

    # High risk modules
    high_risk = sorted(
        [m.to_dict() for m in module_risks if m.coupling_level in (CouplingLevel.HIGH, CouplingLevel.CRITICAL)],
        key=lambda x: -x["coupling_score"],
    )[:_MAX_RESULTS]

    # Coupling summary
    coupling_levels = Counter(m.coupling_level.value for m in module_risks)
    coupling_summary = {
        "total_modules": len(module_risks),
        "total_dependencies": sum(len(d) for d in module_deps.values()),
        "gravity_centers_count": len(gravity_centers),
        "high_risk_count": len(high_risk),
        "low_count": coupling_levels.get("low", 0),
        "medium_count": coupling_levels.get("medium", 0),
        "high_count": coupling_levels.get("high", 0),
        "critical_count": coupling_levels.get("critical", 0),
    }

    # Governance policy checks
    gov_violations: list[dict[str, Any]] = []
    for policy in GOVERNANCE_POLICIES:
        for v in _check_policy(policy, module_deps):
            gov_violations.append(v.to_dict())

    with _lock:
        _violations_store.extend(gov_violations)
        _violations_store[:] = _violations_store[:_violations_max]

    # Hotspots (modules exceeding multiple thresholds)
    hotspots = sorted(
        [
            {
                "module": m.module,
                "reason": "high_fan_in" if m.fan_in >= _COUPLING_THRESHOLDS["fan_in_high"] else "high_fan_out",
                "fan_in": m.fan_in,
                "fan_out": m.fan_out,
                "coupling_score": round(m.coupling_score, 4),
                "level": m.coupling_level.value,
            }
            for m in module_risks
            if m.fan_in >= _COUPLING_THRESHOLDS["fan_in_medium"] or m.fan_out >= _COUPLING_THRESHOLDS["fan_out_medium"]
        ],
        key=lambda x: -x["coupling_score"],
    )[:_MAX_RESULTS]

    # Build snapshot
    snap = ArchitectureSnapshot(
        contract_version=ARCHITECTURE_CONTRACT_VERSION,
        timestamp=ts,
        modules_analyzed=len(module_risks),
        total_dependencies=sum(len(d) for d in module_deps.values()),
        gravity_centers=gravity_centers,
        high_risk_modules=high_risk,
        coupling_summary=coupling_summary,
        governance_violations=gov_violations,
        hotspots=hotspots,
    ).to_dict()

    with _lock:
        _cache = dict(snap)
        _cache_ts = ts

    return snap


def get_architecture_summary(*, now: float | None = None) -> dict[str, Any]:
    """Return current architecture snapshot (read-only, cached)."""
    return analyze_architecture(now=now)


def get_architecture_hotspots(*, limit: int = 20, now: float | None = None) -> dict[str, Any]:
    """Return hotspot modules (bounded)."""
    snap = analyze_architecture(now=now)
    hotspots = snap.get("hotspots", [])
    lim = max(1, min(_MAX_RESULTS, int(limit)))
    return {
        "contract_version": ARCHITECTURE_CONTRACT_VERSION,
        "limit": lim,
        "hotspots_total": len(hotspots),
        "hotspots": hotspots[:lim],
    }


def get_architecture_violations(*, limit: int = 50) -> dict[str, Any]:
    """Return recent governance violations (bounded FIFO)."""
    lim = max(1, min(_violations_max, int(limit)))
    with _lock:
        items = list(_violations_store)[-lim:]
        items.reverse()
        total = len(_violations_store)
    return {
        "contract_version": ARCHITECTURE_CONTRACT_VERSION,
        "limit": lim,
        "violations_total": total,
        "violations": items,
    }


def build_architecture_prometheus_metrics() -> str:
    """Render architecture governance metrics as Prometheus text (fail-safe)."""
    try:
        snap = analyze_architecture()
        total_hotspots = float(len(snap.get("hotspots", [])))
        high_risk_count = float(snap.get("coupling_summary", {}).get("high_count", 0))
        critical_count = float(snap.get("coupling_summary", {}).get("critical_count", 0))
        violations_total = float(len(snap.get("governance_violations", [])))
        gravity_count = float(len(snap.get("gravity_centers", [])))
        return (
            f"ailab_architecture_hotspots_total {total_hotspots}\n"
            f"ailab_architecture_critical_modules_total {float(critical_count)}\n"
            f"ailab_architecture_high_risk_total {float(high_risk_count)}\n"
            f"ailab_architecture_governance_violations_total {float(violations_total)}\n"
            f"ailab_architecture_gravity_centers_total {float(gravity_count)}\n"
        )
    except Exception:
        return (
            "ailab_architecture_hotspots_total 0\n"
            "ailab_architecture_critical_modules_total 0\n"
            "ailab_architecture_high_risk_total 0\n"
            "ailab_architecture_governance_violations_total 0\n"
            "ailab_architecture_gravity_centers_total 0\n"
        )
