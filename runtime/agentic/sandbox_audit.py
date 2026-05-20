"""FASE 28.3 — Sandbox Audit Trail.

Append-only JSONL con mutation_class, checksums before/after,
rollback_available y metadata de cada mutacion sandbox.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_AUDIT_DIR = Path("/opt/ai-lab/runtime/state")
_AUDIT_FILE = "sandbox_audit.jsonl"


@dataclass
class SandboxAuditEntry:
    timestamp: float = field(default_factory=time.time)
    execution_id: str = ""
    workflow_id: str = ""
    action_id: str = ""
    mutation_class: str = ""
    mutation_type: str = ""
    target_path: str = ""
    before_checksum: str = ""
    after_checksum: str = ""
    rollback_available: bool = False
    rollback_path: str = ""
    status: str = "success"
    error: str = ""
    size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "timestamp": int(self.timestamp),
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "action_id": self.action_id,
            "mutation_class": self.mutation_class,
            "mutation_type": self.mutation_type,
            "target_path": self.target_path,
            "before_checksum": self.before_checksum,
            "after_checksum": self.after_checksum,
            "rollback_available": self.rollback_available,
            "rollback_path": self.rollback_path,
            "status": self.status,
            "error": self.error,
            "size_bytes": self.size_bytes,
        }


def _ensure_audit_dir() -> Path:
    _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return _AUDIT_DIR


def write_sandbox_audit(entry: SandboxAuditEntry) -> None:
    audit_dir = _ensure_audit_dir()
    audit_path = audit_dir / _AUDIT_FILE
    line = json.dumps(entry.to_dict(), ensure_ascii=False, default=str)
    try:
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def read_sandbox_audit(limit: int = 50) -> list[dict]:
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


def get_sandbox_audit_stats() -> dict:
    entries = read_sandbox_audit(limit=5000)
    total = len(entries)
    rollback_count = sum(1 for e in entries if e.get("status") == "rollback")
    failed = sum(1 for e in entries if e.get("status") == "failed")
    blocked = sum(1 for e in entries if e.get("status") == "blocked")
    return {
        "total": total,
        "rollback_count": rollback_count,
        "failed": failed,
        "blocked": blocked,
        "success": total - rollback_count - failed - blocked,
        "last_entries": entries[-10:] if entries else [],
    }
