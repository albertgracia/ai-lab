"""FASE 28.3 — Artifact Registry.

Registro de outputs sandbox con lineage DAG (parent_workflow_id,
parent_artifact_id, generated_by_action). Persistencia JSONL.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_REGISTRY_DIR = Path("/opt/ai-lab/runtime/state")
_REGISTRY_FILE = "sandbox_artifacts.jsonl"


@dataclass
class ArtifactEntry:
    artifact_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    path: str = ""
    checksum_sha256: str = ""
    size_bytes: int = 0
    mutation_type: str = ""
    workflow_id: str = ""
    action_id: str = ""
    parent_workflow_id: str = ""
    parent_artifact_id: str = ""
    generated_by_action: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "checksum_sha256": self.checksum_sha256,
            "size_bytes": self.size_bytes,
            "mutation_type": self.mutation_type,
            "workflow_id": self.workflow_id,
            "action_id": self.action_id,
            "parent_workflow_id": self.parent_workflow_id,
            "parent_artifact_id": self.parent_artifact_id,
            "generated_by_action": self.generated_by_action,
            "created_at": int(self.created_at),
            "metadata": self.metadata,
        }


class ArtifactRegistry:
    _registry_path: Path = _REGISTRY_DIR / _REGISTRY_FILE

    @classmethod
    def _ensure_dir(cls) -> Path:
        _REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
        return _REGISTRY_DIR

    @classmethod
    def register(cls, entry: ArtifactEntry) -> None:
        cls._ensure_dir()
        line = json.dumps(entry.to_dict(), ensure_ascii=False, default=str)
        try:
            with open(cls._registry_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    @classmethod
    def _read_all(cls) -> list[dict]:
        if not cls._registry_path.exists():
            return []
        entries = []
        try:
            with open(cls._registry_path, "r", encoding="utf-8") as f:
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
        return entries

    @classmethod
    def list(cls, limit: int = 50) -> list[dict]:
        return cls._read_all()[-limit:]

    @classmethod
    def get(cls, artifact_id: str) -> dict | None:
        for entry in cls._read_all():
            if entry.get("artifact_id") == artifact_id:
                return entry
        return None

    @classmethod
    def get_by_workflow(cls, workflow_id: str) -> list[dict]:
        return [e for e in cls._read_all() if e.get("workflow_id") == workflow_id]

    @classmethod
    def get_lineage(cls, artifact_id: str) -> list[dict]:
        lineage = []
        all_entries = cls._read_all()
        entry_map = {e["artifact_id"]: e for e in all_entries}
        current = entry_map.get(artifact_id)
        while current:
            lineage.append(current)
            parent_id = current.get("parent_artifact_id", "")
            current = entry_map.get(parent_id) if parent_id else None
        return lineage

    @classmethod
    def count_by_workflow(cls, workflow_id: str) -> int:
        return sum(1 for e in cls._read_all() if e.get("workflow_id") == workflow_id)

    @classmethod
    def total_bytes_by_workflow(cls, workflow_id: str) -> int:
        return sum(
            e.get("size_bytes", 0)
            for e in cls._read_all()
            if e.get("workflow_id") == workflow_id
        )
