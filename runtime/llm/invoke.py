from pathlib import Path
import sys
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))

from runtime.prompt.prompt_builder import search, build_prompt
from runtime.router.router import route


LMSTUDIO_API = "http://192.168.1.200:1234/v1/chat/completions"
MODEL = "google/gemma-3-12b"


def call_llm(prompt: str):
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are the AI-Lab Cognitive Runtime."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 1200,
    }

    response = requests.post(
        LMSTUDIO_API,
        json=payload,
        timeout=300
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 runtime/llm/invoke.py "request"')
        sys.exit(1)

    user_request = " ".join(sys.argv[1:])

    routing = route(user_request)
    print(f"[0] Selected Agent: {routing['agent']}")

    print("[1] Semantic Search...")
    results = search(user_request)

    print("[2] Building Prompt...")
    base_prompt = build_prompt(user_request, results)
    prompt = routing["agent_prompt"] + "\n\n" + base_prompt

    print("[3] Invoking LLM...\n")
    answer = call_llm(prompt)

    print("=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()
