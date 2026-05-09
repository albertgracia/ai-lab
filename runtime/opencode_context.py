from pathlib import Path

ROOT = Path("/opt/ai-lab")

CONTEXT_FILES = [
    ROOT / "config/opencode/AI_LAB_CONTEXT.md",
    ROOT / "config/opencode/POLICY.md",
    ROOT / "config/opencode/MODEL_STRATEGY.md",
    ROOT / "runtime/state/system_snapshot.json",
]


def build_opencode_context():
    blocks = []

    for path in CONTEXT_FILES:
        if path.exists():
            blocks.append(f"# FILE: {path}\n\n{path.read_text(errors='ignore')}")

    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    print(build_opencode_context())
