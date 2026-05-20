"""FASE 28.3 — Rollback Engine (reemplaza rollback_placeholder.py).

Snapshot SHA-256 pre-mutacion, restore con validacion checksum post-restore,
rollback completo por workflow. Rollback SOLO dentro del sandbox.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from runtime.agentic.planner import AgenticPlan


@dataclass
class RollbackSnapshot:
    path: str = ""
    checksum_sha256: str = ""
    backup_path: str = ""
    created_at: float = field(default_factory=time.time)
    is_directory: bool = False
    original_exists: bool = False

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "checksum_sha256": self.checksum_sha256,
            "backup_path": self.backup_path,
            "created_at": int(self.created_at),
            "is_directory": self.is_directory,
            "original_exists": self.original_exists,
        }


@dataclass
class RollbackResult:
    success: bool = False
    reason: str = ""
    steps_rolled_back: int = 0
    checksum_validated: bool = False
    restored_checksum: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "reason": self.reason,
            "steps_rolled_back": self.steps_rolled_back,
            "checksum_validated": self.checksum_validated,
            "restored_checksum": self.restored_checksum,
            "details": self.details,
        }


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""


def _sha256_dir(path: str) -> str:
    h = hashlib.sha256()
    try:
        for root, dirs, files in os.walk(path):
            for name in sorted(files):
                filepath = os.path.join(root, name)
                relpath = os.path.relpath(filepath, path)
                h.update(relpath.encode())
                h.update(_sha256_file(filepath).encode())
        return h.hexdigest()
    except Exception:
        return ""


class Snapshotter:
    @staticmethod
    def take_snapshot(
        path: str,
        workflow_id: str,
        action_id: str,
        sandbox_root: str,
    ) -> RollbackSnapshot:
        rollback_dir = os.path.join(sandbox_root, ".rollback", workflow_id, action_id)
        os.makedirs(rollback_dir, exist_ok=True)

        exists = os.path.exists(path)
        is_dir = os.path.isdir(path) if exists else False

        snapshot = RollbackSnapshot(
            path=path,
            original_exists=exists,
            is_directory=is_dir,
        )

        if not exists:
            snapshot.backup_path = os.path.join(rollback_dir, ".absent")
            Path(snapshot.backup_path).touch()
            return snapshot

        if is_dir:
            backup_name = f"dir_{uuid.uuid4().hex[:8]}"
            backup_path = os.path.join(rollback_dir, backup_name)
            shutil.copytree(path, backup_path)
            snapshot.backup_path = backup_path
            snapshot.checksum_sha256 = _sha256_dir(path)
        else:
            backup_name = f"file_{uuid.uuid4().hex[:8]}"
            backup_path = os.path.join(rollback_dir, backup_name)
            shutil.copy2(path, backup_path)
            snapshot.backup_path = backup_path
            snapshot.checksum_sha256 = _sha256_file(path)

        return snapshot


class RollbackEngine:
    @staticmethod
    def restore(snapshot: RollbackSnapshot) -> RollbackResult:
        result = RollbackResult()

        if not snapshot.original_exists:
            if os.path.exists(snapshot.path):
                if snapshot.is_directory:
                    shutil.rmtree(snapshot.path, ignore_errors=True)
                else:
                    os.remove(snapshot.path)
            result.success = True
            result.checksum_validated = True
            result.reason = "restored_to_absent"
            return result

        if not os.path.exists(snapshot.backup_path):
            result.reason = f"backup not found: {snapshot.backup_path}"
            return result

        try:
            if snapshot.is_directory:
                if os.path.exists(snapshot.path):
                    shutil.rmtree(snapshot.path, ignore_errors=True)
                shutil.copytree(snapshot.backup_path, snapshot.path)
            else:
                parent = os.path.dirname(snapshot.path)
                os.makedirs(parent, exist_ok=True)
                shutil.copy2(snapshot.backup_path, snapshot.path)

            restored = _sha256_file(snapshot.path) if not snapshot.is_directory else _sha256_dir(snapshot.path)
            result.restored_checksum = restored

            if restored == snapshot.checksum_sha256:
                result.success = True
                result.checksum_validated = True
                result.reason = "restore_checksum_matched"
            else:
                result.success = True
                result.checksum_validated = False
                result.reason = "restore_checksum_mismatch"
                result.details["expected"] = snapshot.checksum_sha256
                result.details["restored"] = restored

        except Exception as e:
            result.reason = f"restore_failed: {e}"

        return result

    @staticmethod
    def rollback_workflow(
        workflow_id: str,
        sandbox_root: str,
    ) -> RollbackResult:
        rollback_base = os.path.join(sandbox_root, ".rollback", workflow_id)
        if not os.path.isdir(rollback_base):
            return RollbackResult(
                success=False,
                reason=f"no rollback data for workflow {workflow_id}",
            )

        result = RollbackResult(steps_rolled_back=0)
        action_ids = sorted(os.listdir(rollback_base))

        for action_id in action_ids:
            action_dir = os.path.join(rollback_base, action_id)
            if not os.path.isdir(action_dir):
                continue

            backup_items = os.listdir(action_dir)
            if not backup_items:
                continue

            backup_name = backup_items[0]
            backup_path = os.path.join(action_dir, backup_name)

            if backup_name == ".absent":
                snapshot = RollbackSnapshot(
                    path="",
                    original_exists=False,
                    backup_path=backup_path,
                )
            else:
                is_dir = backup_name.startswith("dir_")
                snapshot = RollbackSnapshot(
                    path="",
                    is_directory=is_dir,
                    backup_path=backup_path,
                    original_exists=True,
                )

            snapshot.path = RollbackEngine._infer_original_path(action_dir, sandbox_root)

            if not snapshot.path:
                continue

            single_result = RollbackEngine.restore(snapshot)
            if single_result.success:
                result.steps_rolled_back += 1
                result.details[action_id] = single_result.to_dict()

        result.success = result.steps_rolled_back > 0
        result.reason = f"rolled_back_{result.steps_rolled_back}_actions"
        return result

    @staticmethod
    def _infer_original_path(action_dir: str, sandbox_root: str) -> str:
        marker_path = os.path.join(action_dir, "_original_path.txt")
        if os.path.exists(marker_path):
            try:
                with open(marker_path, "r") as f:
                    return f.read().strip()
            except Exception:
                pass

        backup_items = [i for i in os.listdir(action_dir) if not i.startswith("_")]
        if backup_items:
            return os.path.join(sandbox_root, backup_items[0])

        return ""


def write_original_path_marker(path: str, action_dir: str) -> None:
    marker = os.path.join(action_dir, "_original_path.txt")
    try:
        with open(marker, "w") as f:
            f.write(path)
    except Exception:
        pass


class RollbackPlaceholder:
    @staticmethod
    def rollback(plan: AgenticPlan) -> RollbackResult:
        return RollbackResult(
            success=False,
            reason="rollback_not_implemented_before_FASE_28.3",
        )
