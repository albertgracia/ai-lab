from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any


GC_CONTRACT_VERSION = "28.4"


_PROTECTED_PATTERNS = (
    "33a-", "33b-",
    "28_4-", "28.4-",
    "ailab-", "ai-lab-",
)


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def _now() -> float:
    return 0.0 if _strict_mode() else time.time()


def _is_protected(path: Path) -> bool:
    name = path.name.lower()
    if any(p in name for p in _PROTECTED_PATTERNS):
        return True
    if name.startswith("cp-") and name.endswith("-stable"):
        return True
    return False


def build_gc_inventory(tmp_dir: str = "/tmp") -> dict[str, Any]:
    root = Path(tmp_dir)
    items = []
    if root.exists():
        for p in sorted(root.glob("*")):
            try:
                if not p.is_file():
                    continue
                stat = p.stat()
                items.append({
                    "path": str(p),
                    "name": p.name,
                    "size_bytes": int(stat.st_size),
                    "mtime": int(stat.st_mtime),
                    "protected": _is_protected(p),
                    "lifecycle": "protected" if _is_protected(p) else "gc_candidate",
                })
            except Exception:
                continue

    return {
        "contract_version": GC_CONTRACT_VERSION,
        "generated_at": _now(),
        "tmp_dir": tmp_dir,
        "items": items,
        "total_items": len(items),
    }


def protect_governance_artifacts(inventory: dict[str, Any]) -> dict[str, Any]:
    protected = 0
    for it in inventory.get("items", []) or []:
        if "33a-" in str(it.get("name", "")).lower() or "governance" in str(it.get("name", "")).lower():
            it["protected"] = True
            it["lifecycle"] = "protected"
            protected += 1
    inventory["protected_governance_total"] = protected
    return inventory


def protect_active_validation_artifacts(inventory: dict[str, Any]) -> dict[str, Any]:
    protected = 0
    for it in inventory.get("items", []) or []:
        if "33b-" in str(it.get("name", "")).lower() or "validation" in str(it.get("name", "")).lower():
            it["protected"] = True
            it["lifecycle"] = "protected"
            protected += 1
    inventory["protected_validation_total"] = protected
    return inventory


def protect_runtime_authority_artifacts(inventory: dict[str, Any]) -> dict[str, Any]:
    protected = 0
    for it in inventory.get("items", []) or []:
        name = str(it.get("name", "")).lower()
        if "remediation" in name or "observability" in name or "topology" in name:
            it["protected"] = True
            it["lifecycle"] = "protected"
            protected += 1
    inventory["protected_authority_total"] = protected
    return inventory


def detect_gc_candidates(inventory: dict[str, Any], *, max_age_days: int = 7) -> list[dict[str, Any]]:
    now = time.time()
    candidates = []
    for it in inventory.get("items", []) or []:
        if it.get("protected"):
            continue
        mtime = it.get("mtime", 0)
        age_days = (now - float(mtime)) / 86400.0 if mtime else 0
        if age_days >= max_age_days and it.get("size_bytes", 0) > 0:
            candidates.append({
                "path": it.get("path"),
                "name": it.get("name"),
                "age_days": round(age_days, 1),
                "size_bytes": it.get("size_bytes"),
                "recommended_action": "archive" if str(it.get("name", "")).endswith((".json", ".md", ".log")) else "expire",
                "dry_run": True,
            })
    return candidates


def calculate_gc_safety_score(inventory: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    protected = sum(1 for it in inventory.get("items", []) or [] if it.get("protected"))
    total = len(inventory.get("items", []) or [])
    ratio = protected / max(total, 1)
    # Safer when more protected items and fewer candidates.
    base = 0.7 + min(0.3, ratio * 0.3)
    base -= min(0.4, len(candidates) * 0.01)
    score = round(max(0.0, min(1.0, base)) * 100, 1)
    level = "high" if score >= 85 else "medium" if score >= 65 else "low" if score >= 40 else "critical"
    return {
        "gc_safety_score": score,
        "gc_safety_level": level,
        "protected_ratio": round(ratio, 2),
        "candidates_total": len(candidates),
        "contract_version": GC_CONTRACT_VERSION,
        "generated_at": _now(),
    }


def build_gc_execution_plan(inventory: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Dry-run plan only. Never executes destructive operations."""
    actions = []
    for c in candidates:
        actions.append({
            "action": "archive" if c.get("recommended_action") == "archive" else "expire",
            "path": c.get("path"),
            "dry_run": True,
            "reason": f"age_days={c.get('age_days')} max_age_days exceeded",
        })

    return {
        "contract_version": GC_CONTRACT_VERSION,
        "execution_surface": {
            "SAFE_TO_EXECUTE": True,
            "SAFE_TO_DELETE": False,
            "SAFE_TO_ARCHIVE": False,
            "SAFE_TO_ROTATE": False,
            "SAFE_TO_EXPIRE": False,
            "dry_run_only": True,
        },
        "actions": actions,
        "total_actions": len(actions),
    }
