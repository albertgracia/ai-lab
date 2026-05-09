from pathlib import Path
import sys
import requests
import json

sys.path.append(str(Path(__file__).resolve().parents[2]))

from runtime.prompt.prompt_builder import search, build_prompt
from runtime.router.router import route
from runtime.planner.tool_planner import execute_plan


LMSTUDIO_API = "http://192.168.1.200:1234/v1/chat/completions"
MODEL = "google/gemma-4-e4b"


def call_llm(prompt: str):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are the AI-Lab Cognitive Runtime. You reason using memory, skills, agent context and safe tool results."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1400,
    }

    response = requests.post(
        LMSTUDIO_API,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def format_tool_results(tool_results):
    if not tool_results:
        return "No tools were executed for this request."

    blocks = []

    for item in tool_results:
        command = item["command"]
        result = item["result"]

        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        error = result.get("error", "")
        returncode = result.get("returncode", "")

        blocks.append(
            f"""### Tool Command
$ {command}

Return code: {returncode}

STDOUT:
{stdout[:3000]}

STDERR:
{stderr[:3000]}

ERROR:
{error}
"""
        )

    return "\n\n".join(blocks)


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 runtime/llm/invoke.py "request"')
        sys.exit(1)

    user_request = " ".join(sys.argv[1:])

    routing = route(user_request)
    print(f"[0] Selected Agent: {routing['agent']}")

    print("[1] Semantic Search...")
    results = search(user_request)

    print("[2] Executing Safe Tools...")
    tool_results = execute_plan(user_request)

    print("[3] Building Prompt...")
    base_prompt = build_prompt(user_request, results)
    tool_context = format_tool_results(tool_results)

    prompt = f"""{routing["agent_prompt"]}

{base_prompt}

## Safe Tool Results

{tool_context}

## Final Reasoning Instructions

Use the tool results as live system evidence.
If tool output shows errors, identify the likely root cause.
Recommend safe next steps.
Do not propose destructive changes without explicit confirmation.
"""

    print("[4] Invoking LLM...\n")
    answer = call_llm(prompt)

    print("=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()
