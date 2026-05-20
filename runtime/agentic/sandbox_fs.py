"""FASE 28.3 — Sandbox Filesystem Foundation.

Sandbox roots fijos, path resolution, boundary enforcement,
symlink/traversal detection, path depth limiting.
"""

from __future__ import annotations

import os
from pathlib import Path


SANDBOX_ROOTS = [
    os.path.realpath("/tmp/opencode/sandbox/"),
    os.path.realpath("/opt/ai-lab/sandbox/"),
]

MAX_PATH_DEPTH = 8

BLOCKED_EXTENSIONS = frozenset({
    ".socket", ".service", ".mount", ".timer", ".path", ".target",
    ".swap", ".device", ".automount",
})

ALLOWED_EXTENSIONS = frozenset({
    ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".py", ".sh", ".csv", ".log",
})


def resolve_sandbox_path(path: str, sandbox_root: str) -> str:
    abs_path = os.path.abspath(os.path.join(sandbox_root, path))
    canonical = os.path.realpath(abs_path)
    return canonical


def is_within_sandbox(canonical_path: str, sandbox_roots: list[str] | None = None) -> bool:
    if sandbox_roots is None:
        sandbox_roots = SANDBOX_ROOTS
    for root in sandbox_roots:
        resolved_root = os.path.realpath(root)
        if canonical_path == resolved_root or canonical_path.startswith(resolved_root + os.sep):
            return True
    return False


def ensure_sandbox_dir(sandbox_root: str) -> Path:
    Path(sandbox_root).mkdir(parents=True, exist_ok=True)
    return Path(sandbox_root)


def detect_symlink_escape(path: str, sandbox_root: str) -> bool:
    resolved_root = os.path.realpath(sandbox_root)
    resolved_path = os.path.realpath(path)
    if resolved_path == resolved_root or resolved_path.startswith(resolved_root + os.sep):
        return False
    return True


def detect_path_traversal(path: str) -> bool:
    if ".." in [p for p in path.split(os.sep) if p]:
        return True
    decoded = path.replace("%2F", "/").replace("%2f", "/")
    decoded = decoded.replace("%5C", "\\").replace("%5c", "\\")
    if ".." in [p for p in decoded.split("/") if p]:
        return True
    if "\\" in path and ".." in [p for p in path.split("\\") if p]:
        return True
    if "%2E%2E" in path.upper():
        return True
    normalized = os.path.normpath(path)
    if ".." in normalized.split(os.sep):
        return True
    if normalized.startswith("~"):
        return True
    if os.path.isabs(normalized) and not normalized.startswith("/"):
        return True
    return False


def check_path_depth(path: str, max_depth: int = MAX_PATH_DEPTH) -> bool:
    normalized = os.path.normpath(path)
    parts = [p for p in normalized.split(os.sep) if p and p != "."]
    return len(parts) <= max_depth


def is_extension_allowed(ext: str) -> bool:
    return ext.lower() in ALLOWED_EXTENSIONS


def is_extension_blocked(ext: str) -> bool:
    return ext.lower() in BLOCKED_EXTENSIONS
