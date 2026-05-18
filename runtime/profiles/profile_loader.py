"""Cognitive profile loader for AI-LAB FASE 21.

Loads policy bundles from runtime/profiles/*.json and applies them to
chat completion payloads. Each profile declares model, inference params,
tools policy, memory policy, reasoning policy, streaming and output format.

Priority: client_explicit > profile_default > system_fallback
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_PROFILES_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _PROFILES_DIR / "manifest_profiles.json"

_cache: dict[str, dict] = {}
_manifest: dict | None = None
_manifest_mtime: float = 0.0


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge *override* into *base* recursively. override wins on conflict."""
    result = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def _read_manifest() -> dict:
    global _manifest, _manifest_mtime
    mtime = _MANIFEST_PATH.stat().st_mtime if _MANIFEST_PATH.exists() else 0.0
    if _manifest is not None and mtime == _manifest_mtime:
        return _manifest
    try:
        _manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        _manifest_mtime = mtime
        return _manifest
    except Exception:
        _manifest = {"version": "0", "default_profile": "chat_profile.json", "routes": {}, "overrides": {}}
        _manifest_mtime = 0.0
        return _manifest


def load_profile(name: str) -> dict:
    if name in _cache:
        return _cache[name]
    path = _PROFILES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Profile not found: {path}")
    profile = json.loads(path.read_text(encoding="utf-8"))
    _cache[name] = profile
    return profile


def get_profile_name(route_family: str) -> str:
    manifest = _read_manifest()
    routes = manifest.get("routes", {})
    family = (route_family or "").lower()
    if family in routes:
        return routes[family]
    return manifest.get("default_profile", "chat_profile.json")


def get_profile_for_route(route_family: str) -> dict:
    """Return the full profile dict for a route, with overrides merged."""
    try:
        name = get_profile_name(route_family)
        profile = load_profile(name)
    except Exception:
        profile = {
            "profile": "fallback",
            "version": "0",
            "model": {"default": "llama-3.1-8b-instruct", "fallback": "llama-3.1-8b-instruct"},
            "inference": {"max_tokens": 256, "temperature": 0.2, "top_p": 0.95},
            "tools": {"allowed": False},
            "memory": {"policy": "minimal"},
            "reasoning": {"policy": "disabled"},
            "streaming": {"enabled": True, "preferred": True},
            "output": {"format": "text", "sanitize": True, "no_wrappers": []},
        }

    manifest = _read_manifest()
    overrides = manifest.get("overrides", {}).get(route_family, {})
    if overrides:
        profile = _deep_merge(profile, overrides)

    return profile


def _respect_none(value: Any, default: Any) -> Any:
    """Return *value* if it is a meaningful override (not None), else *default*."""
    if value is None:
        return default
    return value


def apply_profile(payload: dict, route_family: str) -> dict:
    """Apply profile defaults to *payload*. Never overrides explicit client values.

    Returns a new dict with profile metadata injected.
    """
    profile = get_profile_for_route(route_family)
    p = dict(payload)

    model = profile.get("model", {})
    inference = profile.get("inference", {})
    tools_cfg = profile.get("tools", {})
    reasoning_cfg = profile.get("reasoning", {})

    # ── model ───────────────────────────────────────────────────────
    client_model = (p.get("model") or "").strip()
    if not client_model or client_model in ("auto", "default", ""):
        p["model"] = model.get("default", "qwen2.5-coder-14b-instruct")

    # ── inference ────────────────────────────────────────────────────
    client_tokens = _respect_none(p.get("max_tokens"), None)
    if client_tokens is not None and (not isinstance(client_tokens, (int, float)) or client_tokens <= 0):
        client_tokens = None
    if client_tokens is None:
        p["max_tokens"] = inference.get("max_tokens", 512)

    client_temp = _respect_none(p.get("temperature"), None)
    if client_temp is not None and (not isinstance(client_temp, (int, float))):
        client_temp = None
    if client_temp is None:
        p["temperature"] = inference.get("temperature", 0.4)

    p.setdefault("top_p", inference.get("top_p", 0.95))

    # ── tools ────────────────────────────────────────────────────────
    if not tools_cfg.get("allowed", False):
        p.pop("tools", None)
        p.pop("tool_choice", None)

    # ── reasoning ────────────────────────────────────────────────────
    if reasoning_cfg.get("policy") == "disabled":
        p.pop("reasoning", None)

    # ── profile metadata (for observability) ─────────────────────────
    p["_profile"] = profile.get("profile", "unknown")
    p["_profile_version"] = profile.get("version", "0")

    return p
