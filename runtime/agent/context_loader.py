from pathlib import Path

ROOT = Path("/opt/ai-lab")

MAX_FILE_CHARS = 12000
MAX_TOTAL_CHARS = 60000
MAX_RAG_BLOCK_CHARS = 1500

CORE_CONTEXT_FILES = [
    "OPENCODE.md",
    "config/opencode/AI_LAB_CONTEXT.md",
    "config/opencode/POLICY.md",
    "config/opencode/MODEL_STRATEGY.md",
    ".agent/OPENCODE_PROMPT.md",
    ".agent/ARCHITECTURE.md",
    ".agent/rules/GEMINI.md",
    "runtime/policies/evidence_policy.md",
    "memory/tasks/current-roadmap.md",
]

MEMORY_GLOBS = [
    "memory/semantic/*.md",
    "memory/decisions/*.md",
    "memory/summaries/*.md",
]

AGENT_INDEX_FILES = [
    ".agent/BOOTSTRAP.md",
    ".agent/agents/orchestrator.md",
    ".agent/skills/intelligent-routing/SKILL.md",
    ".agent/skills/bash-linux/SKILL.md",
    ".agent/skills/server-management/SKILL.md",
    ".agent/skills/systematic-debugging/SKILL.md",
    ".agent/skills/documentation-templates/SKILL.md",
]


def read_file(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text[:MAX_FILE_CHARS]
    except Exception as exc:
        return f"[ERROR reading {path}: {exc}]"


def collect_files():
    files = []

    for rel in CORE_CONTEXT_FILES:
        path = ROOT / rel
        if path.exists() and path.is_file():
            files.append(path)

    for rel in AGENT_INDEX_FILES:
        path = ROOT / rel
        if path.exists() and path.is_file():
            files.append(path)

    for pattern in MEMORY_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.exists() and path.is_file():
                files.append(path)

    seen = set()
    unique = []

    for path in files:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)

    return unique


def load_semantic_context(user_request: str | None = None, limit: int = 5) -> str:
    if not user_request:
        return ""

    try:
        from runtime.memory.search_memory import search_memory

        results = search_memory(
            query=user_request,
            limit=limit,
        )

    except Exception as exc:
        return (
            "\n\n---\n\n"
            "# SEMANTIC MEMORY ERROR\n\n"
            f"{exc}\n"
        )

    blocks = []

    for item in results:
        path = (
            item.get("file")
            or item.get("path")
            or item.get("source")
            or "unknown"
        )

        score = item.get("score")

        text = (
            item.get("text")
            or item.get("content")
            or ""
        )[:MAX_RAG_BLOCK_CHARS]

        blocks.append(
            f"""### Semantic Result
File: {path}
Score: {score}

{text}
"""
        )

    if not blocks:
        return ""

    return (
        "\n\n---\n\n"
        "# SEMANTIC MEMORY RETRIEVAL\n\n"
        + "\n\n".join(blocks)
    )


def build_agent_context(user_request: str | None = None) -> str:
    blocks = []

    blocks.append(
        """# AI-LAB AGENT CONTEXT

This context is loaded from the local AI-LAB repository.

Rules:
- Always answer in Spanish.
- Do not invent files, services, ports, logs or configuration.
- Prefer read-only diagnostics before changes.
- Separate FACTS from HYPOTHESES.
- Do not perform destructive actions without explicit approval.
- Use the local .agent layer, policies, skills, rules and memory as operational context.
- Use semantic memory retrieval as supporting context, but do not copy it literally.
"""
    )

    if user_request:
        blocks.append(f"# CURRENT USER REQUEST\n\n{user_request[:4000]}")

    semantic_context = load_semantic_context(user_request)

    if semantic_context:
        blocks.append(semantic_context)

    total = 0

    for path in collect_files():
        rel = path.relative_to(ROOT)
        content = read_file(path)

        block = f"\n\n---\n\n# FILE: {rel}\n\n{content}"

        if total + len(block) > MAX_TOTAL_CHARS:
            blocks.append(
                "\n\n---\n\n# CONTEXT TRUNCATED\n\nContext limit reached. Additional files were not included."
            )
            break

        blocks.append(block)
        total += len(block)

    return "\n".join(blocks)


if __name__ == "__main__":
    print(build_agent_context("AI-LAB cognitive routing and governance"))
