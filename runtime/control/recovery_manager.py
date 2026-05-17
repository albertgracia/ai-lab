"""Recovery Manager — snapshot, restore, and health recovery policies.

Provides:
  create_snapshot(reason)       → snapshot current state
  preview_recovery_changes(sid) → diff before restore
  recover_from_snapshot(sid)    → restore state files
  health_recovery_policies()    → recommended actions for degraded states
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

_STATE_DIR = Path("/opt/ai-lab/runtime/state")
_SNAPSHOT_DIR = _STATE_DIR / "snapshots"

_SNAPSHOT_FILES = [
    "current_mode.json",
    "cluster_state.json",
    "routing_history.jsonl",
]


def create_snapshot(reason: str = "") -> dict[str, Any]:
    """Create a timestamped snapshot of critical state files."""
    _SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    sid = f"snap-{int(time.time())}"
    snap_path = _SNAPSHOT_DIR / sid
    snap_path.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    skipped: list[str] = []
    for fname in _SNAPSHOT_FILES:
        src = _STATE_DIR / fname
        if src.exists():
            shutil.copy2(src, snap_path / fname)
            saved.append(fname)
        else:
            skipped.append(fname)

    meta = {
        "snapshot_id": sid,
        "created_at": int(time.time()),
        "reason": reason,
        "saved": saved,
        "skipped": skipped,
    }
    (snap_path / "_meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    return meta


def preview_recovery_changes(snapshot_id: str) -> dict[str, Any]:
    """Show what would change before performing a restore."""
    snap_path = _SNAPSHOT_DIR / snapshot_id
    if not snap_path.exists():
        return {"error": f"snapshot {snapshot_id} not found"}

    changes: dict[str, Any] = {}
    for fname in _SNAPSHOT_FILES:
        snap_file = snap_path / fname
        live_file = _STATE_DIR / fname
        if not snap_file.exists():
            changes[fname] = "not_in_snapshot"
        elif not live_file.exists():
            changes[fname] = "would_create"
        else:
            changes[fname] = "would_overwrite"
    return {"snapshot_id": snapshot_id, "changes": changes}


def recover_from_snapshot(snapshot_id: str) -> dict[str, Any]:
    """Restore state files from a snapshot."""
    snap_path = _SNAPSHOT_DIR / snapshot_id
    if not snap_path.exists():
        return {"error": f"snapshot {snapshot_id} not found"}

    restored: list[str] = []
    failed: list[str] = []
    for fname in _SNAPSHOT_FILES:
        src = snap_path / fname
        dst = _STATE_DIR / fname
        if src.exists():
            try:
                shutil.copy2(src, dst)
                restored.append(fname)
            except Exception:
                failed.append(fname)

    return {
        "snapshot_id": snapshot_id,
        "restored": restored,
        "failed": failed,
        "ok": len(failed) == 0,
    }


def list_snapshots() -> list[dict[str, Any]]:
    """List available snapshots."""
    if not _SNAPSHOT_DIR.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for snap_path in sorted(_SNAPSHOT_DIR.iterdir(), reverse=True):
        meta_file = snap_path / "_meta.json"
        if meta_file.exists():
            try:
                snapshots.append(json.loads(meta_file.read_text()))
            except Exception:
                pass
    return snapshots


def health_recovery_policies() -> dict[str, Any]:
    """Return recommended actions for known degraded states."""
    try:
        from runtime.control.control_plane import get_governance_state
        state = get_governance_state()
    except Exception:
        state = "NORMAL"

    policies: dict[str, list[str]] = {
        "NORMAL": [],
        "ELEVATED": [
            "review blocked actions in Grafana governance dashboard",
            "check LM Studio model response quality",
        ],
        "DEGRADED": [
            "restart ailab-router to clear parser state",
            "verify Qdrant connectivity: curl http://127.0.0.1:6333/health",
            "check disk space on /opt/ai-lab",
        ],
        "LOCKDOWN": [
            "create snapshot before recovery: POST /api/control/snapshots",
            "restart ailab-gateway and ailab-router",
            "verify Prometheus scrape targets: http://192.168.1.40:9090/targets",
            "if Qdrant degraded: docker restart qdrant",
        ],
    }

    return {
        "governance_state": state,
        "recommended_actions": policies.get(state, []),
    }
