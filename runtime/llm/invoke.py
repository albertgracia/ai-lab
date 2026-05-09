from pathlib import Path
import sys
import requests
import json

sys.path.append(str(Path(__file__).resolve().parents[2]))

from runtime.prompt.prompt_builder import search, build_prompt
from runtime.router.router import route
from runtime.planner.tool_planner import execute_plan
from runtime.llm.model_router import select_node
from runtime.state.system_state import build_system_state


# ============================================================
# POLICY
# ============================================================

POLICY_PATH = Path("/opt/ai-lab/runtime/policy/system_policy.md")


def load_policy():
    if POLICY_PATH.exists():
        return POLICY_PATH.read_text()

    return ""


SYSTEM_PROMPT = f"""
You are the AI-Lab Cognitive Runtime.

You are operating inside Albert's local AI-Lab infrastructure.

ALWAYS respond in Spanish.
NEVER switch to English unless explicitly requested.

Be concise but technical.

Use evidence from:
- semantic memory
- runtime infrastructure state
- verified tool execution
- agent specialization

Never hallucinate infrastructure state.
Never invent files, ports, containers, YAML, logs or services.

Always distinguish:
- FACT
- HYPOTHESIS
- RECOMMENDATION

Environment includes:
- Ubuntu Server VM in Hyper-V
- Docker
- Traefik
- Qdrant
- Open WebUI
- LM Studio distributed inference nodes
- Multi-agent runtime
- Semantic search
- Local-first architecture

Current inference architecture:
- RX9070XT node → fast orchestration and lightweight reasoning
- RX7900XT node → deep reasoning, debugging and coding
- Main LM Studio node → fallback/general inference

{load_policy()}
"""


# ============================================================
# LLM CALL
# ============================================================

def call_llm(prompt: str, node: dict):
    api_url = f"http://{node['host']}:{node['port']}/v1/chat/completions"

    payload = {
        "model": node["model"],
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
    }

    response = requests.post(
        api_url,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


# ============================================================
# TOOL FORMATTER
# ============================================================

def format_tool_results(tool_results):
    if not tool_results:
        return "No tools were executed."

    blocks = []

    for item in tool_results:
        command = item["command"]
        result = item["result"]

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        error = result.get("error", "")
        returncode = result.get("returncode", "")

        blocks.append(
            f"""
### TOOL COMMAND
$ {command}

RETURN CODE:
{returncode}

STDOUT:
{stdout[:4000]}

STDERR:
{stderr[:4000]}

ERROR:
{error}
"""
        )

    return "\n\n".join(blocks)


# ============================================================
# MAIN
# ============================================================

def main():
    if len(sys.argv) < 2:
        print('Usage: python runtime/llm/invoke.py "request"')
        sys.exit(1)

    user_request = " ".join(sys.argv[1:])

    # --------------------------------------------------------
    # MODEL ROUTING
    # --------------------------------------------------------

    node = select_node(user_request)

    print(
        f"[N] Selected Inference Node: "
        f"{node['name']} "
        f"({node['host']}:{node['port']})"
    )

    print(f"[N] Selected Model: {node['model']}")

    # --------------------------------------------------------
    # AGENT ROUTING
    # --------------------------------------------------------

    routing = route(user_request)

    print(f"[0] Selected Agent: {routing['agent']}")

    # --------------------------------------------------------
    # SEMANTIC SEARCH
    # --------------------------------------------------------

    print("[1] Semantic Search...")

    results = search(user_request)

    # --------------------------------------------------------
    # RUNTIME STATE
    # --------------------------------------------------------

    print("[1.5] Building Runtime State...")

    runtime_state = build_system_state()

    runtime_context = json.dumps(
        runtime_state,
        indent=2
    )

    # --------------------------------------------------------
    # SAFE TOOLS
    # --------------------------------------------------------

    print("[2] Executing Safe Tools...")

    tool_results = execute_plan(user_request)

    tool_context = format_tool_results(tool_results)

    # --------------------------------------------------------
    # PROMPT BUILD
    # --------------------------------------------------------

    print("[3] Building Prompt...")

    base_prompt = build_prompt(
        user_request,
        results
    )

    prompt = f"""
{routing["agent_prompt"]}

{base_prompt}

# RUNTIME INFRASTRUCTURE STATE

{runtime_context}

# VERIFIED TOOL OUTPUT

{tool_context}

# FINAL REASONING INSTRUCTIONS

Use runtime infrastructure state as REAL infrastructure evidence.

Use tool outputs as VERIFIED live evidence.

Never invent:
- containers
- services
- ports
- YAML
- TOML
- logs
- routing rules
- infrastructure state

If evidence is incomplete:
- explicitly say so

Prefer grounded reasoning over speculation.

Always respond in Spanish.
"""

    # --------------------------------------------------------
    # LLM INVOCATION
    # --------------------------------------------------------

    print("[4] Invoking LLM...\n")

    answer = call_llm(prompt, node)

    print("=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()