"""Declarative prompt loader for AI-LAB runtime.

Loads prompt text from versioned .md files keyed by route family / capability.
Rejects prompts that contain forbidden legacy markers for non-cognitive routes.

Usage:
    from runtime.prompts.prompt_loader import get_prompt_for_route
    system_text = get_prompt_for_route("chat", "fast")
"""

from __future__ import annotations

import json
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _PROMPTS_DIR / "manifest.json"

_cache: dict[str, str] = {}
_manifest: dict | None = None
_manifest_mtime: float = 0.0


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
        _manifest = {"version": "0", "default": "chat_prompt.md", "routes": {}}
        _manifest_mtime = 0.0
        return _manifest


def _load_prompt_file(name: str) -> str:
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_prompt(name: str) -> str:
    if name in _cache:
        return _cache[name]

    text = _load_prompt_file(name)
    _cache[name] = text
    return text


def validate_prompt(text: str, route_key: str) -> list[str]:
    """Return list of forbidden markers found in *text* for *route_key*."""
    manifest = _read_manifest()
    forbidden = manifest.get("forbidden_markers", {}).get(route_key, [])
    if not forbidden:
        return []

    hits: list[str] = []
    lower = text.lower()
    for marker in forbidden:
        if marker.lower() in lower:
            hits.append(marker)
    return hits


def get_prompt_name(route_family: str, capability: str = "") -> str:
    """Map a route family and capability to a prompt file name."""
    manifest = _read_manifest()
    routes = manifest.get("routes", {})

    family = (route_family or "").lower()
    cap = (capability or "").lower()

    if family == "minimal":
        return routes.get(family, routes.get("minimal", manifest["default"]))

    if cap in routes:
        return routes[cap]

    if family in routes:
        return routes[family]

    return manifest.get("default", "chat_prompt.md")


def get_prompt_for_route(route_family: str, capability: str = "") -> tuple[str, list[str]]:
    """Return (prompt_text, [warnings]) for a route family.

    The prompt is loaded from its .md file and validated against forbidden markers.
    If loading or validation fails, a fallback minimal prompt is returned.
    """
    try:
        name = get_prompt_name(route_family, capability)
        text = load_prompt(name)
    except Exception:
        return (
            "Responde en espanol, breve y natural. No uses JSON ni herramientas.",
            ["prompt_load_failed"],
        )

    route_key = route_family
    if route_key == "minimal" or capability in ("minimal", "casual", "greeting", "report"):
        route_key = "minimal"
    elif capability in ("fast", "general", "chat") or route_family in ("fast", "general", "chat", "cognitive"):
        route_key = "chat"
    elif capability == "coding" or route_family == "coding":
        route_key = "coding"
    elif capability == "observe" or route_family == "observe":
        route_key = "observe"

    warnings = validate_prompt(text, route_key)
    return text, warnings
