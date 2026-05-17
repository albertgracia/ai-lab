"""Mode Manager — read and switch runtime operational mode.

Persists mode in runtime/state/current_mode.json.
Transitions:
  readonly → plan: automatic
  plan     → build: requires confirm
  build    → execute: requires confirm + reason
  any      → readonly/plan/build: free
"""

import json
import time
from pathlib import Path
from typing import Optional

MODE_FILE = Path("/opt/ai-lab/runtime/state/current_mode.json")

VALID_MODES = ("readonly", "plan", "observe", "build", "execute")

# Allowed transitions without extra validation
_AUTO_TRANSITIONS = {
    "readonly": ("plan",),
    "plan": ("readonly", "observe", "build", "execute"),
    "observe": ("readonly", "plan", "build", "execute"),
    "build": ("readonly", "plan", "observe", "execute"),
    "execute": ("readonly", "plan", "observe", "build"),
}

# Transitions that require explicit reason
_REQUIRE_REASON = {
    ("plan", "execute"),
    ("build", "execute"),
    ("readonly", "execute"),
    ("observe", "execute"),
}


def _default_state(mode: str = "plan") -> dict:
    return {
        "mode": mode,
        "updated_at": int(time.time()),
        "updated_by": "system",
        "previous_mode": "plan",
    }


def read_mode() -> dict:
    """Read current mode from file. Returns default if file missing/corrupt."""
    if not MODE_FILE.exists():
        state = _default_state()
        write_mode(state["mode"], "system")
        return state
    try:
        data = json.loads(MODE_FILE.read_text())
        if data.get("mode") not in VALID_MODES:
            data["mode"] = "plan"
        return data
    except (json.JSONDecodeError, KeyError):
        return _default_state()


def write_mode(mode: str, updated_by: str = "api", reason: str = "") -> dict:
    """Persist a new mode to file."""
    prev = read_mode()
    state = {
        "mode": mode,
        "updated_at": int(time.time()),
        "updated_by": updated_by,
        "previous_mode": prev.get("mode", "plan"),
        "reason": reason or None,
    }
    MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    return state


def current_mode() -> str:
    """Return just the mode string (fast, no parsing overhead)."""
    return read_mode().get("mode", "plan")


def can_transition(from_mode: str, to_mode: str) -> tuple[bool, str]:
    """Check if a mode transition is valid.

    Returns:
        (allowed: bool, message: str)
    """
    if from_mode not in VALID_MODES:
        return False, f"Invalid current mode: {from_mode}"
    if to_mode not in VALID_MODES:
        return False, f"Invalid target mode: {to_mode}"
    if from_mode == to_mode:
        return False, f"Already in {to_mode} mode"

    allowed = _AUTO_TRANSITIONS.get(from_mode, ())
    if to_mode in allowed:
        return True, ""
    return False, f"Cannot transition from {from_mode} to {to_mode} directly"


def requires_reason(from_mode: str, to_mode: str) -> bool:
    """Whether the transition needs an explicit reason."""
    return (from_mode, to_mode) in _REQUIRE_REASON
