from pathlib import Path

from runtime.agent.intent_router import (
    RouteDecision,
    route_request,
)

ROOT = Path("/opt/ai-lab")

MAX_FILE_CHARS = 12000
MAX_TOTAL_CHARS = 40000

AGENT_DIR = ROOT / ".agent" / "agents"
SKILLS_DIR = ROOT / ".agent" / "skills"
WORKFLOW_DIR = ROOT / ".agent" / "workflows"


def read_file(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore"
        )[:MAX_FILE_CHARS]

    except Exception as exc:
        return f"[ERROR reading {path}: {exc}]"


def load_agent_file(agent_name: str):
    path = AGENT_DIR / f"{agent_name}.md"

    if path.exists():
        return path

    return None


def load_skill_files(skills: list[str]):
    files = []

    for skill in skills:

        skill_dir = SKILLS_DIR / skill

        if not skill_dir.exists():
            continue

        skill_file = skill_dir / "SKILL.md"

        if skill_file.exists():
            files.append(skill_file)

    return files


def load_workflow_file(workflow: str | None):

    if not workflow:
        return None

    path = WORKFLOW_DIR / f"{workflow}.md"

    if path.exists():
        return path

    return None


def build_selective_context(
    user_request: str
):

    decision: RouteDecision = route_request(
        user_request
    )

    blocks = []

    blocks.append(
        f"""# AI-LAB SELECTIVE CONTEXT

Agent:
{decision.agent}

Reasoning:
{decision.reasoning}

Complexity:
{decision.complexity}

Workflow:
{decision.workflow}

Domains:
{", ".join(decision.domains)}

Multi Agent:
{decision.multi_agent}
"""
    )

    blocks.append(
        f"""

# USER REQUEST

{user_request}
"""
    )

    selected_files = [
        ROOT / "OPENCODE.md",
        ROOT / "config/opencode/AI_LAB_CONTEXT.md",
        ROOT / "config/opencode/POLICY.md",
        ROOT / "config/opencode/MODEL_STRATEGY.md",
        ROOT / ".agent/OPENCODE_PROMPT.md",
    ]

    agent_file = load_agent_file(
        decision.agent
    )

    if agent_file:
        selected_files.append(agent_file)

    selected_files.extend(
        load_skill_files(
            decision.skills
        )
    )

    workflow_file = load_workflow_file(
        decision.workflow
    )

    if workflow_file:
        selected_files.append(
            workflow_file
        )

    total = 0

    for path in selected_files:

        if not path.exists():
            continue

        try:
            rel = path.relative_to(ROOT)
        except Exception:
            rel = path

        content = read_file(path)

        block = (
            f"\n\n---\n\n"
            f"# FILE: {rel}\n\n"
            f"{content}"
        )

        if total + len(block) > MAX_TOTAL_CHARS:

            blocks.append(
                """

---

# CONTEXT TRUNCATED

Selective context limit reached.
"""
            )

            break

        blocks.append(block)

        total += len(block)

    return "\n".join(blocks)


if __name__ == "__main__":

    test_request = (
        "Audita seguridad de OpenWebUI y Ollama en AI-LAB"
    )

    print(
        build_selective_context(
            test_request
        )
    )
