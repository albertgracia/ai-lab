"""Working Memory — per-session cognitive state.

Maintains conversation history, task continuity, and files-touched
tracking across requests within a single session.  The ``digest()``
method uses a *simple heuristic* (last N important turns) — no LLM
summarisation — to avoid latency, drift, and hallucination.

A new ``WorkingMemory`` is created for every session_id; sessions
live in a module-level dict and are lost on restart (acceptable for v1).
"""

import time
from pathlib import Path

# ── module-level session store ──────────────────────────────────────────
_sessions: dict[str, "WorkingMemory"] = {}

# ── task → token budget (approximate, in characters) ────────────────────
_TASK_BUDGETS = {
    "coding": 6_000,       # needs space for code, less context
    "fast": 4_000,          # minimum context for quick answers
    "reasoning": 12_000,    # needs broad context for analysis
    "general": 8_000,
    "embeddings": 2_000,
    "vision": 4_000,
}

_MAX_CONVERSATION_TURNS = 30
_DIGEST_TURNS = 8


class WorkingMemory:
    """Per-session working state."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.current_task: str | None = None
        self.conversation: list[tuple[str, str]] = []   # (role, content)
        self.files_touched: set[str] = set()
        self.skills_used: set[str] = set()
        self.agent_name: str | None = None
        self.tokens_budget: int = 8_000
        self.context_aging: dict[str, float] = {}  # source_name →  last_access_ts
        self.created_at = time.time()
        self.last_update = time.time()

    # ── conversation infrastructure ─────────────────────────────────

    def add_turn(self, role: str, content: str):
        """Append one conversation turn (user or assistant)."""
        self.conversation.append((role, content))
        if len(self.conversation) > _MAX_CONVERSATION_TURNS:
            self.conversation = self.conversation[-_MAX_CONVERSATION_TURNS:]
        self.last_update = time.time()

    def set_task(self, task_type: str):
        """Update the current task and adjust the token budget."""
        self.current_task = task_type
        self.tokens_budget = _TASK_BUDGETS.get(task_type, 8_000)

    def touch_file(self, path: str):
        """Mark a file as accessed (for context aging)."""
        self.files_touched.add(path)
        self.context_aging[path] = self.last_update

    def touch_skill(self, skill: str):
        self.skills_used.add(skill)

    # ── digest (no LLM) ─────────────────────────────────────────────

    def digest(self, max_turns: int | None = None) -> str:
        """Return a compact summary of recent conversation activity.

        Uses the last *N* important turns — no external LLM call.
        Long messages are truncated to 200 chars each.
        """
        max_turns = max_turns or _DIGEST_TURNS
        recent = self.conversation[-max_turns:]

        parts: list[str] = []
        for role, content in recent:
            preview = content[:200] + "..." if len(content) > 200 else content
            parts.append(f"[{role}]: {preview}")

        return "\n".join(parts)

    # ── persistence stubs ────────────────────────────────────────────

    @classmethod
    def stats(cls) -> dict:
        """Aggregated stats across all active sessions."""
        sessions = list(_sessions.values())
        n = len(sessions)
        if n == 0:
            return {"sessions": 0, "avg_turns": 0, "avg_digest_size": 0, "largest_session": 0}
        return {
            "sessions": n,
            "avg_turns": round(sum(len(s.conversation) for s in sessions) / n, 1),
            "avg_digest_size": round(sum(len(s.digest()) for s in sessions) / n, 1),
            "largest_session": max((len(s.conversation) for s in sessions), default=0),
        }

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "current_task": self.current_task,
            "conversation_length": len(self.conversation),
            "files_touched": sorted(self.files_touched),
            "skills_used": sorted(self.skills_used),
            "agent_name": self.agent_name,
            "tokens_budget": self.tokens_budget,
            "created_at": self.created_at,
            "last_update": self.last_update,
        }

    def __repr__(self) -> str:
        return (
            f"WorkingMemory(session={self.session_id}, "
            f"task={self.current_task}, "
            f"turns={len(self.conversation)}, "
            f"budget={self.tokens_budget})"
        )


# ── public API ───────────────────────────────────────────────────────────

def get_session(session_id: str) -> WorkingMemory:
    """Retrieve or create the WorkingMemory for *session_id*."""
    if session_id not in _sessions:
        _sessions[session_id] = WorkingMemory(session_id)
    return _sessions[session_id]


def active_sessions() -> int:
    """Number of sessions currently held in memory."""
    return len(_sessions)


def evict_old_sessions(max_age_seconds: int = 3600):
    """Remove sessions that haven't been touched in *max_age_seconds*."""
    now = time.time()
    stale = [
        sid for sid, wm in _sessions.items()
        if now - wm.last_update > max_age_seconds
    ]
    for sid in stale:
        del _sessions[sid]
    return len(stale)
