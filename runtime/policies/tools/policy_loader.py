"""Tool policy loader for AI-LAB FASE 22A.

Loads declarative tool policies from runtime/policies/tools/*.json and applies
them to chat completion payloads. Filters tools by mode (disabled/readonly/agentic),
blocked names (global master + per-policy), and allowed names.

Priority: blocked_master > policy.blocked_names > policy.allowed_names > guards
"""

from __future__ import annotations

import json
from pathlib import Path

_POLICIES_DIR = Path(__file__).resolve().parent
_MANIFEST_PATH = _POLICIES_DIR / "manifest_tools.json"
_BLOCKED_MASTER_PATH = _POLICIES_DIR / "blocked_tools.json"

_cache: dict[str, dict] = {}
_manifest: dict | None = None
_blocked_master: dict | None = None


def _read_manifest() -> dict:
    global _manifest
    if _manifest is not None:
        return _manifest
    try:
        _manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
        return _manifest
    except Exception:
        _manifest = {"version": "0", "default": "disabled_policy.json", "profiles": {}}
        return _manifest


def _read_blocked_master() -> dict:
    global _blocked_master
    if _blocked_master is not None:
        return _blocked_master
    try:
        _blocked_master = json.loads(_BLOCKED_MASTER_PATH.read_text(encoding="utf-8"))
        return _blocked_master
    except Exception:
        _blocked_master = {"blocked_names": [], "blocked_tool_types": []}
        return _blocked_master


def load_tool_policy(name: str) -> dict:
    if name in _cache:
        return _cache[name]
    path = _POLICIES_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Tool policy not found: {path}")
    policy = json.loads(path.read_text(encoding="utf-8"))
    _cache[name] = policy
    return policy


def get_policy_for_profile(profile_name: str) -> dict:
    manifest = _read_manifest()
    profiles = manifest.get("profiles", {})
    name = profiles.get(profile_name, manifest.get("default", "disabled_policy.json"))
    try:
        return load_tool_policy(name)
    except Exception:
        return {
            "policy": "fallback",
            "mode": "disabled",
            "requires_confirmation": False,
            "max_tool_calls": 0,
            "allowed_names": [],
            "blocked_names": [],
            "audit_required": False,
        }


def _tool_name(tool: dict) -> str:
    if not isinstance(tool, dict):
        return ""
    fn = tool.get("function") if isinstance(tool.get("function"), dict) else {}
    return str(fn.get("name") or tool.get("name") or "").strip()


def _tool_type(tool: dict) -> str:
    if not isinstance(tool, dict):
        return ""
    return str(tool.get("type") or "").strip().lower()


def apply_tool_policy(payload: dict, policy: dict) -> dict:
    """Apply tool policy to *payload*.

    Returns a new dict with tools filtered and metadata injected.
    """
    def _audit_tool(tool_name: str, result: str, reason: str = ""):
        try:
            from runtime.audit.audit_logger import audit_event
            audit_event(result, {
                "tool_name": tool_name,
                "policy": policy.get("policy", "unknown"),
                "mode": mode,
                "profile": p.get("_profile", payload.get("_profile", "unknown")),
                "route": payload.get("_ai_lab_route_family", "unknown"),
                "reason": reason,
            })
        except ImportError:
            pass

    def _sanitize_bash(tool: dict) -> bool:
        """Returns True if bash tool passes sanitization."""
        if _tool_name(tool) != "bash":
            return True
        try:
            from runtime.policies.tools.bash_sanitizer import sanitize_bash_command
            fn = tool.get("function", {}) if isinstance(tool.get("function"), dict) else {}
            cmd = str(fn.get("arguments", "") or fn.get("command", ""))
            safe, warnings, needs_confirm = sanitize_bash_command(cmd, policy)
            if safe is None:
                for w in warnings:
                    _audit_tool("bash", "tool_call_blocked_by_policy", f"bash_sanitizer: {w}")
                return False
            if needs_confirm and not p.get("_tool_requires_confirmation"):
                p["_tool_requires_confirmation"] = True
            return True
        except ImportError:
            return True

    p = dict(payload)
    master = _read_blocked_master()
    mode = policy.get("mode", "disabled")

    master_blocked = set(master.get("blocked_names", []))
    master_blocked_types = set(master.get("blocked_tool_types", []))
    policy_blocked = set(policy.get("blocked_names", []))
    policy_allowed = set(policy.get("allowed_names", []))
    all_blocked = master_blocked | policy_blocked

    tools = p.get("tools")
    if not isinstance(tools, list) or not tools:
        p.pop("tools", None)
        p.pop("tool_choice", None)
        p["_tool_policy"] = policy.get("policy", "unknown")
        p["_tool_mode"] = mode
        p["_tool_source"] = "manifest_tools"
        return p

    if mode == "disabled":
        for tool in tools:
            _audit_tool(_tool_name(tool) or "unknown", "tool_call_blocked_by_policy", "mode=disabled")
        p["_tool_budget_original"] = len(tools)
        p["_tool_budget_limit"] = policy.get("max_tool_calls", 0)
        p.pop("tools", None)
        p.pop("tool_choice", None)

    elif mode == "readonly":
        filtered = []
        for tool in tools:
            name = _tool_name(tool)
            ttype = _tool_type(tool)
            if not name:
                continue
            if name in all_blocked:
                _audit_tool(name, "tool_call_blocked_by_policy", "blocked_name")
                continue
            if ttype in master_blocked_types:
                _audit_tool(name, "tool_call_blocked_by_policy", "blocked_type")
                continue
            if policy_allowed and name not in policy_allowed:
                _audit_tool(name, "tool_call_blocked_by_policy", "not_in_allowed")
                continue
            if not _sanitize_bash(tool):
                continue
            _audit_tool(name, "tool_call_allowed")
            filtered.append(tool)
        if filtered:
            p["tools"] = filtered
            budget = policy.get("max_tool_calls", 5)
            p["_tool_budget_original"] = len(tools)
            p["_tool_budget_limit"] = budget
            if len(filtered) > budget:
                p["tools"] = filtered[:budget]
                p["_tool_budget_exceeded"] = True
        else:
            p["_tool_budget_original"] = len(tools)
            p["_tool_budget_limit"] = policy.get("max_tool_calls", 5)
            p.pop("tools", None)
            p.pop("tool_choice", None)

    elif mode == "agentic":
        filtered = []
        for tool in tools:
            name = _tool_name(tool)
            ttype = _tool_type(tool)
            if not name:
                continue
            if name in master_blocked:
                _audit_tool(name, "tool_call_blocked_by_policy", "master_blocked")
                continue
            if ttype in master_blocked_types:
                _audit_tool(name, "tool_call_blocked_by_policy", "master_blocked_type")
                continue
            if name in policy_blocked:
                _audit_tool(name, "tool_call_blocked_by_policy", "policy_blocked")
                continue
            if not _sanitize_bash(tool):
                continue
            _audit_tool(name, "tool_call_allowed")
            filtered.append(tool)
        if filtered:
            p["tools"] = filtered
            budget = policy.get("max_tool_calls", 20)
            p["_tool_budget_original"] = len(tools)
            p["_tool_budget_limit"] = budget
            if len(filtered) > budget:
                p["tools"] = filtered[:budget]
                p["_tool_budget_exceeded"] = True
        else:
            p["_tool_budget_original"] = len(tools)
            p["_tool_budget_limit"] = policy.get("max_tool_calls", 20)
            p.pop("tools", None)
            p.pop("tool_choice", None)

    p["_tool_policy"] = policy.get("policy", "unknown")
    p["_tool_mode"] = mode
    p["_tool_source"] = "manifest_tools"
    if policy.get("requires_confirmation", False):
        p["_tool_requires_confirmation"] = True

    return p
