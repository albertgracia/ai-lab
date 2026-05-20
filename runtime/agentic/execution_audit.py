from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


_AUDIT_DIR = Path("/opt/ai-lab/runtime/state")
_AUDIT_FILE = "execution_audit.jsonl"


def _ensure_audit_dir() -> Path:
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return _AUDIT_DIR


def write_execution_audit(entry: dict) -> None:
    audit_dir = _ensure_audit_dir()
    audit_path = audit_dir / _AUDIT_FILE
    line = json.dumps(entry, ensure_ascii=False, default=str)
    try:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def build_audit_entry(
    execution_id: str,
    plan_id: str,
    mode: str,
    dry_run: bool,
    dry_run_reason: str | None,
    action: dict,
    result: dict,
    phase: str = "28.2",
) -> dict:
    return {
        "timestamp": int(time.time()),
        "execution_id": execution_id,
        "plan_id": plan_id,
        "phase": phase,
        "execution_mode": mode,
        "dry_run": dry_run,
        "dry_run_reason": dry_run_reason,
        "action": action,
        "result": result,
    }


def read_execution_audit(limit: int = 50) -> list[dict]:
    audit_path = _ensure_audit_dir() / _AUDIT_FILE
    entries = []
    if not audit_path.exists():
        return entries
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    except Exception:
        pass
    return entries[-limit:]


def get_audit_stats() -> dict:
    entries = read_execution_audit(limit=1000)
    total = len(entries)
    blocked = sum(1 for e in entries if e.get("result", {}).get("blocked", False))
    success = sum(1 for e in entries if not e.get("result", {}).get("blocked", False) and e.get("result", {}).get("exit_code", 0) == 0)
    failed = sum(1 for e in entries if not e.get("result", {}).get("blocked", False) and e.get("result", {}).get("exit_code", -1) != 0)
    return {
        "total": total,
        "blocked": blocked,
        "success": success,
        "failed": failed,
        "last_entries": entries[-10:] if entries else [],
    }
