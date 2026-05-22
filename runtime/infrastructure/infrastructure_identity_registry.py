from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from runtime.infrastructure.contracts import (
    INFRASTRUCTURE_CONTRACT_VERSION,
    AuthorityRoot,
    OperationalNode,
    InfrastructureDependency,
    InfrastructureIdentity,
    InfrastructureAuthorityMap,
    InfrastructureInventory,
    InfrastructureSemanticSummary,
)


INFRASTRUCTURE_REGISTRY_VERSION = "35A"


_IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


# ── Canonical identity anchors (authority roots) ────────────────────


_AUTHORITY_ROOTS: dict[str, dict[str, Any]] = {
    "192.168.1.40": {
        "roles": [
            "ROLE-PROMETHEUS-AUTHORITY",
            "ROLE-OBSERVABILITY-BACKBONE",
            "ROLE-GRAFANA-VISUALIZATION",
            "ROLE-HYPERV-HOST",
        ],
        "criticality": "critical",
        "authority_type": "observability",
        "source_of_truth": "prometheus",
        "expected_offline": False,
        "notes": [
            "Prometheus authority root",
            "Grafana datasource root",
            "Telemetry source-of-truth",
        ],
    },
    "192.168.1.30": {
        "roles": [
            "ROLE-RUNTIME-CONTROL-PLANE",
        ],
        "criticality": "critical",
        "authority_type": "control",
        "source_of_truth": "runtime_control_plane",
        "expected_offline": False,
        "notes": ["gateway/router/live-api/docs"],
    },
    "192.168.1.50": {
        "roles": [
            "ROLE-INFERENCE-BACKEND",
            "ROLE-GPU-NODE",
        ],
        "criticality": "high",
        "authority_type": "operational",
        "source_of_truth": "lmstudio",
        "expected_offline": False,
        "notes": ["RX9070 active inference backend"],
    },
    "192.168.1.60": {
        "roles": [
            "ROLE-INVENTORY-OFFLINE",
            "ROLE-NON-ROUTABLE",
            "ROLE-GPU-NODE",
        ],
        "criticality": "low",
        "authority_type": "inventory",
        "source_of_truth": "inventory",
        "expected_offline": True,
        "notes": ["RX7900XT expected_offline inventory-only"],
    },
    "192.168.1.200": {
        "roles": [
            "ROLE-STORAGE",
            "ROLE-EXPORTER",
        ],
        "criticality": "medium",
        "authority_type": "operational",
        "source_of_truth": "nas",
        "expected_offline": False,
        "notes": ["NAS-N5 (SMB)", "exporters/storage"],
    },
}


_ROLE_DESCRIPTIONS: dict[str, str] = {
    "ROLE-PROMETHEUS-AUTHORITY": "Prometheus authority root",
    "ROLE-GRAFANA-VISUALIZATION": "Grafana visualization layer",
    "ROLE-RUNTIME-CONTROL-PLANE": "AI-LAB runtime control plane",
    "ROLE-INFERENCE-BACKEND": "Inference backend (LM Studio)",
    "ROLE-GPU-NODE": "GPU node",
    "ROLE-HYPERV-HOST": "Hyper-V Ubuntu host",
    "ROLE-EXPORTER": "Metrics exporter host",
    "ROLE-STORAGE": "Storage / NAS",
    "ROLE-OBSERVABILITY-BACKBONE": "Observability backbone",
    "ROLE-INVENTORY-OFFLINE": "Inventory-only expected offline",
    "ROLE-DISCOVERABLE": "Discoverable (not necessarily operational)",
    "ROLE-LEGACY": "Legacy entity (non-operational)",
    "ROLE-NON-ROUTABLE": "Non-routable entity",
}


def classify_infrastructure_role(identity: str) -> list[str]:
    info = _AUTHORITY_ROOTS.get(identity)
    if info:
        return list(info.get("roles", []))
    return []


def classify_operational_state(identity: str) -> str:
    info = _AUTHORITY_ROOTS.get(identity)
    if info and bool(info.get("expected_offline")):
        return "inventory_only"
    if info:
        return "operational"
    return "unknown"


def detect_control_plane_nodes() -> list[str]:
    # Deterministic: explicitly anchored.
    return ["192.168.1.30"]


def detect_authority_dependencies() -> list[dict[str, Any]]:
    deps = [
        InfrastructureDependency(
            source="runtime_control_plane",
            depends_on="192.168.1.40",
            reason="telemetry/governance authority via Prometheus",
        ).to_dict(),
        InfrastructureDependency(
            source="reporting",
            depends_on="192.168.1.40",
            reason="observability source-of-truth",
        ).to_dict(),
    ]
    return deps


def _load_discoverable_nodes() -> list[str]:
    """Best-effort discoverable nodes list from runtime/state.

    This is optional and must NOT override authority roots.
    """
    paths = [
        Path("/opt/ai-lab/runtime/state/discovered_nodes.json"),
        Path("runtime/state/discovered_nodes.json"),
    ]
    for p in paths:
        try:
            if p.is_file() and p.stat().st_size > 0:
                data = json.loads(p.read_text(encoding="utf-8"))
                nodes = data.get("nodes", []) or []
                out = []
                for n in nodes:
                    host = str((n or {}).get("host") or "").strip()
                    if host and _IP_RE.search(host):
                        out.append(host)
                return sorted(set(out))
        except Exception:
            continue
    return []


def build_authority_root_map() -> dict[str, Any]:
    roots = []
    for ip in sorted(_AUTHORITY_ROOTS):
        info = _AUTHORITY_ROOTS[ip]
        roots.append(AuthorityRoot(
            identity=ip,
            roles=list(info.get("roles", [])),
            criticality=str(info.get("criticality", "unknown")),
            authority_type=str(info.get("authority_type", "unknown")),
            source_of_truth=str(info.get("source_of_truth", "unknown")),
            expected_offline=bool(info.get("expected_offline")),
        ).to_dict())
    deps = detect_authority_dependencies()
    return InfrastructureAuthorityMap(authority_roots=roots, dependencies=deps).to_dict()


def build_operational_node_map() -> dict[str, Any]:
    op = []
    inv = []
    disc = []
    legacy = []
    unknown: list[str] = []

    discoverable = _load_discoverable_nodes()
    for ip in sorted(set(list(_AUTHORITY_ROOTS.keys()) + discoverable)):
        info = _AUTHORITY_ROOTS.get(ip)
        roles = classify_infrastructure_role(ip) or ([] if info is None else list(info.get("roles", [])))
        expected_offline = bool((info or {}).get("expected_offline"))
        state = classify_operational_state(ip)
        routable = state == "operational" and ("ROLE-INVENTORY-OFFLINE" not in roles)
        node = OperationalNode(
            identity=ip,
            roles=roles,
            operational_state=state,
            expected_offline=expected_offline,
            routable=routable,
            notes=list((info or {}).get("notes", [])) if isinstance((info or {}).get("notes"), list) else [],
        ).to_dict()

        if ip in _AUTHORITY_ROOTS and state == "operational":
            op.append(node)
        elif expected_offline:
            inv.append(node)
        elif ip in discoverable:
            # Discoverable, but not anchored.
            disc.append(node)
        elif ip in _AUTHORITY_ROOTS:
            inv.append(node)
        else:
            unknown.append(ip)

    inv_contract = InfrastructureInventory(
        operational_nodes=op,
        inventory_only_nodes=inv,
        discoverable_nodes=disc,
        legacy_nodes=legacy,
        unknown_nodes=sorted(set(unknown)),
    ).to_dict()
    return inv_contract


def calculate_infrastructure_identity_score(registry: dict[str, Any]) -> dict[str, Any]:
    issues = []
    authority_roots = registry.get("authority_roots", []) or []
    control_plane = registry.get("control_plane", []) or []
    unknown_nodes = (((registry.get("inventory", {}) or {}).get("unknown_nodes")) or [])
    score = 100.0
    if "192.168.1.40" not in authority_roots:
        score -= 60
        issues.append("missing_prometheus_authority_root")
    if "192.168.1.30" not in control_plane:
        score -= 30
        issues.append("missing_control_plane_root")
    if unknown_nodes:
        score -= min(30.0, float(len(unknown_nodes)) * 5.0)
        issues.append("unknown_infrastructure_entities")
    score = max(0.0, min(100.0, score))
    level = "high" if score >= 85 else "medium" if score >= 65 else "low" if score >= 40 else "critical"
    return {
        "contract_version": INFRASTRUCTURE_CONTRACT_VERSION,
        "infrastructure_identity_score": round(score, 1),
        "infrastructure_identity_level": level,
        "issues": issues,
        "deterministic_signature": _hash({"score": round(score, 1), "authority_roots": sorted(authority_roots), "control_plane": sorted(control_plane), "unknown": sorted(unknown_nodes)}),
        "generated_at": _now(),
    }


def build_infrastructure_identity_registry(*, extra_ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    extra_ctx = extra_ctx or {}
    authority_map = build_authority_root_map()
    inventory = build_operational_node_map()
    control_plane = detect_control_plane_nodes()
    authority_roots = sorted([r["identity"] for r in (authority_map.get("authority_roots", []) or []) if isinstance(r, dict) and r.get("identity")])

    base = {
        "contract_version": INFRASTRUCTURE_CONTRACT_VERSION,
        "registry_version": INFRASTRUCTURE_REGISTRY_VERSION,
        "authority_map": authority_map,
        "inventory": inventory,
        "control_plane": sorted(control_plane),
        "authority_roots": authority_roots,
    }
    score = calculate_infrastructure_identity_score(base)
    base["score"] = float(score.get("infrastructure_identity_score", 0.0) or 0.0)
    base["issues"] = score.get("issues", [])
    base["generated_at"] = _now()
    base["deterministic_signature"] = _hash({
        "authority_roots": authority_roots,
        "control_plane": sorted(control_plane),
        "inventory": inventory,
        "issues": base["issues"],
        "score": base["score"],
    })

    if os.environ.get("AI_LAB_ENABLE_INFRASTRUCTURE_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        try:
            Path("/tmp/35a-infrastructure-registry.json").write_text(json.dumps(base, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
            Path("/tmp/35a-authority-roots.json").write_text(json.dumps(authority_map, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
            Path("/tmp/35a-control-plane.json").write_text(json.dumps({"control_plane": sorted(control_plane)}, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
            Path("/tmp/35a-operational-nodes.json").write_text(json.dumps(inventory, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
            Path("/tmp/35a-infrastructure-score.json").write_text(json.dumps(score, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
        except Exception:
            pass

    return base


def build_infrastructure_semantic_summary(identity: str) -> dict[str, Any]:
    identity = (identity or "").strip()
    roles = classify_infrastructure_role(identity)
    info = _AUTHORITY_ROOTS.get(identity) or {}
    expected_offline = bool(info.get("expected_offline"))
    authority_root = identity in _AUTHORITY_ROOTS
    op_state = classify_operational_state(identity)

    if not authority_root:
        summary = f"{identity}: unknown infrastructure identity (NO DISPONIBLE)."
    else:
        role_lines = []
        for r in roles:
            role_lines.append(_ROLE_DESCRIPTIONS.get(r, r))
        if expected_offline:
            summary = f"{identity}: inventory-only expected_offline (non-operational). Roles: {', '.join(role_lines) if role_lines else 'unknown'}."
        else:
            summary = f"{identity}: operational node. Roles: {', '.join(role_lines) if role_lines else 'unknown'}."

    contract = InfrastructureSemanticSummary(
        contract_version=INFRASTRUCTURE_CONTRACT_VERSION,
        identity=identity,
        roles=roles,
        summary=summary,
        authority_root=authority_root,
        expected_offline=expected_offline,
        operational_state=op_state,
        deterministic_signature=_hash({"identity": identity, "roles": sorted(roles), "authority_root": authority_root, "expected_offline": expected_offline, "op_state": op_state}),
    ).to_dict()

    if os.environ.get("AI_LAB_ENABLE_INFRASTRUCTURE_ARTIFACTS", "true").lower() in ("true", "1", "yes"):
        try:
            Path("/tmp/35a-semantic-summary.json").write_text(json.dumps(contract, sort_keys=True, ensure_ascii=True, default=str) + "\n", encoding="utf-8")
        except Exception:
            pass

    return contract


def identify_infrastructure(text: str) -> dict[str, Any]:
    """Extract an IP and return its infrastructure identity.

    RULE-35A-7: no hallucinated infrastructure.
    """
    t = str(text or "")
    m = _IP_RE.search(t)
    if not m:
        return {
            "contract_version": INFRASTRUCTURE_CONTRACT_VERSION,
            "status": "unknown",
            "identity": None,
            "summary": "NO DISPONIBLE",
        }
    ip = m.group(0)
    rep = build_infrastructure_semantic_summary(ip)
    rep["status"] = "ok" if rep.get("authority_root") else "unknown"
    return rep
