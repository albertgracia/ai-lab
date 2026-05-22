from pathlib import Path
import subprocess
import json
import sys

ROOT = Path("/opt/ai-lab")

# Anti-stale guard: minimum expected checkpoint
MINIMUM_CHECKPOINT = "CP-33A"
CURRENT_CHECKPOINT_TAG = "CP-33A-RUNTIME-GOVERNANCE-REGISTRY-STABLE"
CURRENT_CHECKPOINT_COMMIT = "HEAD"

CONTEXT_FILES = [
    ROOT / "config/opencode/AI_LAB_CONTEXT.md",
    ROOT / "config/opencode/POLICY.md",
    ROOT / "config/opencode/MODEL_STRATEGY.md",
    ROOT / "runtime/state/system_snapshot.json",
]


def get_current_git_tag() -> str:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=5
        )
        tag = result.stdout.strip()
        if tag:
            return tag
    except Exception:
        pass
    return CURRENT_CHECKPOINT_TAG


def anti_stale_guard() -> str | None:
    actual_tag = get_current_git_tag()
    if actual_tag.startswith("CP-"):
        major = actual_tag.split("-")[1] if "-" in actual_tag else ""
        expected_major = MINIMUM_CHECKPOINT.split("-")[1] if "-" in MINIMUM_CHECKPOINT else ""
        if major and expected_major:
            try:
                actual_num = int(major.replace("CP", ""))
                expected_num = int(expected_major.replace("CP", ""))
                if actual_num < expected_num:
                    return (
                        f"WARNING: Context stale. "
                        f"Expected checkpoint >= {MINIMUM_CHECKPOINT}, "
                        f"got {actual_tag}. "
                        f"Refresh OpenCode runtime context from {ROOT} before proceeding."
                    )
            except ValueError:
                pass
    return None


def build_runtime_truth_block() -> str:
    tag = get_current_git_tag()
    lines = [
        "=== CURRENT AI-LAB RUNTIME TRUTH (HARD FACTS) ===",
        "",
        f"Current checkpoint: {tag}",
        f"Runtime root: {ROOT}",
        f"Runtime data: /opt/ai-lab-data",
        f"Models: /mnt/ai-models",
        f"Archives: /mnt/opencode/ai-lab-archives",
        "",
        "Operational model routing:",
        "- llama-3.1-8b-instruct = PRIMARY_OPERATIONAL_MODEL",
        "- qwen/qwen2.5-coder-14b-instruct = PRIMARY_CODING_MODEL",
        "- nomic-embed-text-v1.5 = embedding model",
        "- lmstudio-community/qwen2.5-coder-14b-instruct = DEPRECATED / NON_ROUTABLE",
        "- qwen3.6-27b = DESACTIVADO (tests manuales)",
        "- qwen2.5-coder-32b = DOWN (RX7900XT offline)",
        "",
        "Active GPU:",
        "- RX9070 / 192.168.1.50 / active_inference_backend",
        "",
        "Inventory offline:",
        "- RX7900XT / 192.168.1.60 / expected_offline",
        "",
        "Observability:",
        "- Prometheus authority = 192.168.1.40:9090",
        "- Grafana visualization layer = 192.168.1.40:3000",
        "- Loki log layer",
        "- Grafana is NOT source of truth",
        "",
        "Next planned phase: FASE 28.4 - Tool Contracts & Cross-Plan GC",
        "",
        "Runtime APIs (source_of_truth for UI):",
        "- /runtime/entities      → entity registry with active/inventory/deprecated",
        "- /runtime/topology      → topology graph with nodes, edges, degraded paths",
        "- /runtime/maturity      → runtime maturity score and state",
        "- /runtime/ui-alignment  → UI alignment validator score and drift detection",
        "- /runtime/grounding     → runtime grounding envelope",
        "- /runtime/reporting/*   → operational reports",
        "- /runtime/observability/* → observability audit",
        "- /runtime/governance    → governance registry with domains, authority, risks, score, contracts, remediation",
        "",
        "UI is runtime-driven. No hardcoded GPUs (RTX5070, A100). No fake inventory.",
        "",
        "Do not suggest old phases unless explicitly requested.",
        "Do not reference CP-30Z or earlier as current state.",
        "",
    ]
    return "\n".join(lines)


def build_opencode_context():
    blocks = []

    stale_warning = anti_stale_guard()
    if stale_warning:
        blocks.append(f"# STALE CONTEXT WARNING\n\n{stale_warning}")

    blocks.append(build_runtime_truth_block())

    for path in CONTEXT_FILES:
        if path.exists():
            blocks.append(f"# FILE: {path}\n\n{path.read_text(errors='ignore')}")

    return "\n\n---\n\n".join(blocks)


if __name__ == "__main__":
    if "--validate" in sys.argv:
        warning = anti_stale_guard()
        if warning:
            print(warning)
            sys.exit(1)
        print(f"Context validation PASS: checkpoint >= {MINIMUM_CHECKPOINT}")
        sys.exit(0)
    print(build_opencode_context())
