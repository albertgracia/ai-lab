"""Memory policy loader for AI-LAB FASE 23A.

Loads declarative memory policies from runtime/policies/memory/*.json.
Maps profiles to policies via manifest_memory.json.
"""

from __future__ import annotations

import json
from pathlib import Path

_POLICIES_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _POLICIES_DIR / "manifest_memory.json"

_cache: dict[str, dict] = {}
_manifest: dict | None = None


def _read_manifest() -> dict:
    global _manifest
    if _manifest is not None:
        return _manifest
    try:
        _manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        return _manifest
    except Exception:
        _manifest = {"version": "0", "default": "light_policy.json", "profiles": {}}
        return _manifest


def load_memory_policy(name: str) -> dict:
    if name in _cache:
        return _cache[name]
    path = _POLICIES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Memory policy not found: {path}")
    policy = json.loads(path.read_text(encoding="utf-8"))
    _cache[name] = policy
    return policy


def get_policy_for_profile(profile_name: str) -> dict:
    manifest = _read_manifest()
    profiles = manifest.get("profiles", {})
    name = profiles.get(profile_name, manifest.get("default", "light_policy.json"))
    try:
        return load_memory_policy(name)
    except Exception:
        return {
            "policy": "fallback",
            "semantic_recall": False,
            "episodic_recall": False,
            "max_memories": 0,
            "max_chars": 0,
            "min_score": 0.8,
            "min_query_words": 4,
            "sources": [],
            "inject_runtime_state": False,
        }
