"""Context Shaper — dynamic, task-aware context assembly.

Replaces the hard 40K-char limit of ``selective_context`` with:
  • token budgeting based on model context window (chars ≈ tokens × 2.8)
  • priority scoring per source file (intent-based relevance)
  • context aging (low-priority files lose relevance over time)
  • optional working-memory digest appended at the end

Designed to plug into ``router_api.py`` via try/except ImportError fallback.
"""

import time
from pathlib import Path

# ── source context files (ordered by default priority) ───────────────────
_SOURCE_FILES = [
    Path("/opt/ai-lab/OPENCODE.md"),
    Path("/opt/ai-lab/config/opencode/AI_LAB_CONTEXT.md"),
    Path("/opt/ai-lab/config/opencode/POLICY.md"),
    Path("/opt/ai-lab/config/opencode/MODEL_STRATEGY.md"),
    Path("/opt/ai-lab/.agent/OPENCODE_PROMPT.md"),
]

# ── intent → source-file relevance weights ──────────────────────────────
# Higher weight = more relevant for that task type.
_INTENT_WEIGHTS: dict[str, dict[str, float]] = {
    "coding":    {"OPENCODE": 0.3, "AI_LAB_CONTEXT": 0.5, "POLICY": 0.1, "MODEL_STRATEGY": 0.6, "OPENCODE_PROMPT": 0.4},
    "reasoning":{"OPENCODE": 0.5, "AI_LAB_CONTEXT": 0.8, "POLICY": 0.3, "MODEL_STRATEGY": 0.4, "OPENCODE_PROMPT": 0.3},
    "fast":      {"OPENCODE": 0.2, "AI_LAB_CONTEXT": 0.3, "POLICY": 0.05, "MODEL_STRATEGY": 0.1, "OPENCODE_PROMPT": 0.2},
    "general":   {"OPENCODE": 0.3, "AI_LAB_CONTEXT": 0.4, "POLICY": 0.2, "MODEL_STRATEGY": 0.3, "OPENCODE_PROMPT": 0.3},
    "architecture": {"OPENCODE": 0.6, "AI_LAB_CONTEXT": 1.0, "POLICY": 0.3, "MODEL_STRATEGY": 0.7, "OPENCODE_PROMPT": 0.4},
    "security":  {"OPENCODE": 0.4, "AI_LAB_CONTEXT": 0.5, "POLICY": 0.8, "MODEL_STRATEGY": 0.3, "OPENCODE_PROMPT": 0.2},
}

# ── limits ───────────────────────────────────────────────────────────────
_CHARS_PER_TOKEN_ESTIMATE = 2.8   # user's adjustment to avoid under-use
_MAX_FILE_CHARS = 12_000


def _file_key(path: Path) -> str:
    """Return a short key for a source file (used in intent weights)."""
    stem = path.stem.upper()
    for kw in ["OPENCODE", "AI_LAB_CONTEXT", "POLICY", "MODEL_STRATEGY", "OPENCODE_PROMPT"]:
        if kw in stem or kw in path.name.upper():
            return kw
    return stem


def _read_source(path: Path) -> str:
    """Read a source file returning its text (or empty string)."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


# ── public API ───────────────────────────────────────────────────────────

def shape_context(
    task_type: str,
    model_id: str = "",
    working_memory=None,
) -> str:
    """Return a context string optimised for *task_type* and *model_id*.

    Parameters
    ----------
    task_type : str
        e.g. "coding", "reasoning", "fast", "general".
    model_id : str
        Key in MODEL_REGISTRY (used to determine the context budget).
    working_memory : WorkingMemory | None
        Optional per-session state for conversation digest and file aging.

    Returns
    -------
    str
        Assembled context ready to be injected into the system prompt.
    """
    # ── 1. determine token budget ────────────────────────────────────
    context_window = 32_000   # default fallback
    try:
        from runtime.models.model_registry import MODEL_REGISTRY
        ctx_cfg = MODEL_REGISTRY.get(model_id, {})
        context_window = ctx_cfg.get("context_window", 32_000)
    except ImportError:
        pass

    budget = int(context_window * _CHARS_PER_TOKEN_ESTIMATE)

    # ── 2. load source files ─────────────────────────────────────────
    sources = []
    for sp in _SOURCE_FILES:
        text = _read_source(sp)
        if not text:
            continue
        key = _file_key(sp)
        sources.append({"name": key, "path": str(sp), "text": text, "size": len(text)})

    # ── 3. priority scoring per source ───────────────────────────────
    weights = _INTENT_WEIGHTS.get(task_type, _INTENT_WEIGHTS["general"])

    scored = []
    for s in sources:
        base = weights.get(s["name"], 0.3)

        # context aging: last-access time via working memory
        if working_memory:
            last_access = working_memory.context_aging.get(s["name"], time.time())
            age_hours = max(0, (time.time() - last_access) / 3600.0)
            age_factor = max(0.3, 1.0 - age_hours / 48.0)   # decay over 48 h
            base *= age_factor
            working_memory.context_aging[s["name"]] = time.time()

        scored.append((s, base))

    scored.sort(key=lambda x: x[1], reverse=True)

    # ── 4. fill budget ───────────────────────────────────────────────
    chunks: list[str] = []
    used = 0

    for s, priority in scored:
        if used >= budget:
            break
        remaining = budget - used
        text = s["text"]
        if len(text) > min(_MAX_FILE_CHARS, remaining):
            text = text[: min(_MAX_FILE_CHARS, remaining)] + "\n-- [truncated]"
        chunks.append(f"## {s['name']}\n{text}")
        used += len(text)

    # ── 5. append conversation digest (if working memory available) ───
    if working_memory:
        digest = working_memory.digest()
        if used + len(digest) <= budget:
            chunks.append(f"## Conversation Context\n{digest}")
            used += len(digest)

    return "\n\n---\n\n".join(chunks)
