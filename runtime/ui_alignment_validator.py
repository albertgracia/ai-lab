from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

from runtime.topology import (
    build_runtime_topology,
    detect_topology_drift,
)

ASTRO_ROOT = Path("/opt/ai-lab/apps/ialab-docs/src")

_KNOWN_FAKE_GPUS = {"RTX5070", "RTX 5070", "A100", "NVIDIA A100", "H100", "NVIDIA H100", "H200", "NVIDIA H200", "V100", "Tesla V100", "Tesla T4", "T4"}
_KNOWN_HARDCODED_INVENTORY_PATTERNS = [
    "gpu_1", "gpu_2", "gpu_3", "fake_gpu",
    "rtx5070", "tesla",
]
_KNOWN_LEGITIMATE_GPU_NAMES = {"RX9070", "RX9070XT", "RX7900XT", "RX 9070", "RX 7900 XT", "RX 7900XT"}


def _ensure_list(val: Any) -> list:
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        return [val]
    return []


def _build_runtime_entities() -> list[dict]:
    try:
        from runtime.entities import build_entity_registry
        return build_entity_registry()
    except ImportError:
        return []


def _build_runtime_topology_data() -> dict[str, Any]:
    try:
        return build_runtime_topology()
    except ImportError:
        return {"nodes": [], "edges": [], "degraded_paths": []}


def _gather_ui_entities_from_astro() -> list[dict]:
    """Scan Astro pages and markdown for hardcoded GPU/model references."""
    entities: list[dict] = []
    seen_ids: set[str] = set()
    if not ASTRO_ROOT.exists():
        return entities
    for fpath in sorted(ASTRO_ROOT.rglob("*")):
        if not fpath.is_file():
            continue
        if fpath.suffix not in (".astro", ".md", ".mdx"):
            continue
        try:
            text = fpath.read_text(errors="ignore")
        except Exception:
            continue
        for gpu_name in ("RX9070", "RX9070XT", "RX7900XT", "RX 9070", "RX 7900 XT"):
            if gpu_name in text and gpu_name not in seen_ids:
                seen_ids.add(gpu_name)
                entities.append({
                    "id": gpu_name,
                    "name": gpu_name,
                    "entity_type": "gpu",
                    "source_file": str(fpath.relative_to(ASTRO_ROOT)),
                    "hardcoded": True,
                })
        for fake in _KNOWN_FAKE_GPUS:
            if fake.lower() in text.lower() and fake not in seen_ids:
                seen_ids.add(fake)
                entities.append({
                    "id": fake,
                    "name": fake,
                    "entity_type": "gpu",
                    "source_file": str(fpath.relative_to(ASTRO_ROOT)),
                    "hardcoded": True,
                    "fake": True,
                })
    return entities


def detect_ui_hardcoded_inventory(
    inventory_data: list[dict] | None = None,
) -> list[dict]:
    found: list[dict] = []
    if not inventory_data:
        inventory_data = _gather_ui_entities_from_astro()
    for item in inventory_data:
        item_id = str(item.get("id", item.get("name", ""))).lower()
        if _is_legitimate_gpu(item_id):
            continue
        for pattern in _KNOWN_HARDCODED_INVENTORY_PATTERNS:
            if pattern in item_id:
                found.append({
                    "entity_id": item.get("id", item.get("name", "?")),
                    "pattern": pattern,
                    "reason": f"matches known hardcoded pattern: {pattern}",
                    "severity": "high",
                })
                break
    return found


def _is_legitimate_gpu(name: str) -> bool:
    for legit in _KNOWN_LEGITIMATE_GPU_NAMES:
        if legit.lower() in name.lower():
            return True
    return False


def detect_ui_fake_entities(
    entity_list: list[dict] | None = None,
) -> list[dict]:
    found: list[dict] = []
    if not entity_list:
        entity_list = _gather_ui_entities_from_astro()
    seen: set[str] = set()
    for entity in entity_list:
        eid = str(entity.get("entity_id", entity.get("id", "")))
        ename = str(entity.get("name", ""))
        if _is_legitimate_gpu(eid) or _is_legitimate_gpu(ename):
            continue
        combined = (eid + " " + ename).lower()
        for fake in _KNOWN_FAKE_GPUS:
            if fake.lower() in combined:
                dedup_key = f"fake:{fake}"
                if dedup_key not in seen:
                    seen.add(dedup_key)
                    found.append({
                        "entity_id": eid,
                        "fake_gpu": fake,
                        "reason": f"fake GPU detected: {fake}",
                        "severity": "critical",
                    })
                break
    return found


def detect_ui_topology_drift(
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> list[dict]:
    try:
        return detect_topology_drift(sensor_snapshot, extra_ctx)
    except ImportError:
        return []


def detect_ui_runtime_mismatch(
    ui_entities: list[dict] | None = None,
    runtime_entities: list[dict] | None = None,
) -> list[dict]:
    mismatches: list[dict] = []
    if not ui_entities:
        ui_entities = _gather_ui_entities_from_astro()
    if not runtime_entities:
        runtime_entities = _build_runtime_entities()
    if not ui_entities or not runtime_entities:
        return mismatches
    ui_ids = {e.get("entity_id", e.get("id", "")) for e in ui_entities}
    rt_ids = {e.get("entity_id", "") for e in runtime_entities}
    active_rt_ids = {e.get("entity_id", "") for e in runtime_entities if e.get("operational_state") == "active"}
    for uid in ui_ids:
        if uid and uid not in rt_ids:
            mismatches.append({
                "entity_id": uid,
                "reason": f"entity '{uid}' exists in UI but not in runtime entity registry",
                "severity": "medium",
            })
        elif uid not in active_rt_ids and uid in rt_ids:
            mismatches.append({
                "entity_id": uid,
                "reason": f"entity '{uid}' exists in runtime but is not active (inventory/discoverable/deprecated)",
                "severity": "low",
            })
    return mismatches


def calculate_ui_alignment_score(
    hardcoded_count: int = 0,
    fake_entity_count: int = 0,
    topology_drift_count: int = 0,
    runtime_mismatch_count: int = 0,
    total_ui_entities: int = 1,
) -> dict:
    penalties = 0.0
    details: dict[str, Any] = {}

    if hardcoded_count > 0:
        p = min(1.0, hardcoded_count * 0.2)
        penalties += p
        details["hardcoded_inventory_penalty"] = round(p, 2)
    else:
        details["hardcoded_inventory_penalty"] = 0.0

    if fake_entity_count > 0:
        p = min(1.0, fake_entity_count * 0.3)
        penalties += p
        details["fake_entity_penalty"] = round(p, 2)
    else:
        details["fake_entity_penalty"] = 0.0

    if topology_drift_count > 0:
        p = min(1.0, topology_drift_count * 0.15)
        penalties += p
        details["topology_drift_penalty"] = round(p, 2)
    else:
        details["topology_drift_penalty"] = 0.0

    if runtime_mismatch_count > 0:
        p = min(1.0, runtime_mismatch_count * 0.1)
        penalties += p
        details["runtime_mismatch_penalty"] = round(p, 2)
    else:
        details["runtime_mismatch_penalty"] = 0.0

    base_score = 100.0
    overall = max(0.0, base_score - (penalties * 100.0 / max(total_ui_entities, 1)))

    if overall >= 90:
        level = "high"
    elif overall >= 70:
        level = "medium"
    elif overall >= 50:
        level = "low"
    else:
        level = "critical"

    return {
        "overall_score": round(overall, 1),
        "level": level,
        "factors": details,
        "penalties": {
            "hardcoded_inventory": hardcoded_count,
            "fake_entities": fake_entity_count,
            "topology_drift": topology_drift_count,
            "runtime_mismatch": runtime_mismatch_count,
        },
        "total_ui_entities": total_ui_entities,
    }


def validate_ui_runtime_alignment(
    ui_entities: list[dict] | None = None,
    runtime_entities: list[dict] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
    extra_ctx: dict[str, Any] | None = None,
) -> dict:
    if ui_entities is None:
        ui_entities = _gather_ui_entities_from_astro()
    if runtime_entities is None:
        runtime_entities = _build_runtime_entities()
    topology = _build_runtime_topology_data()

    hardcoded = detect_ui_hardcoded_inventory(ui_entities)
    fake_entities = detect_ui_fake_entities(ui_entities)
    topology_drift = detect_ui_topology_drift(sensor_snapshot or topology, extra_ctx)
    runtime_mismatch = detect_ui_runtime_mismatch(ui_entities, runtime_entities)

    total_ui = len(ui_entities) if ui_entities else 1

    score = calculate_ui_alignment_score(
        hardcoded_count=len(hardcoded),
        fake_entity_count=len(fake_entities),
        topology_drift_count=len(topology_drift),
        runtime_mismatch_count=len(runtime_mismatch),
        total_ui_entities=max(total_ui, 1),
    )

    return {
        "timestamp": time.time(),
        "contract_version": "32A",
        "alignment_score": score,
        "issues": {
            "hardcoded_inventory": hardcoded,
            "fake_entities": fake_entities,
            "topology_drift": topology_drift,
            "runtime_mismatch": runtime_mismatch,
        },
        "summary": {
            "total_hardcoded": len(hardcoded),
            "total_fake": len(fake_entities),
            "total_drift": len(topology_drift),
            "total_mismatch": len(runtime_mismatch),
            "total_issues": len(hardcoded) + len(fake_entities) + len(topology_drift) + len(runtime_mismatch),
        },
    }
