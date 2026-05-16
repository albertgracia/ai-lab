"""Latency baseline: 3 profiles × 3 samples.

Measures TTFB, total time, model, tokens, context_budget_used.
"""

import json
import subprocess
import sys
import time
import os

sys.path.insert(0, "/opt/ai-lab")
from runtime.llm.router_api import LM_STUDIO_MAX_CONTEXT

PROFILES = {
    "fast": {"prompt": "Hola"},
    "coding": {"prompt": "Explica el patron Singleton en Python con un ejemplo de codigo"},
    "reasoning": {"prompt": "Si tuvieras que migrar de LM Studio a vLLM, que factores considerarias para mantener latencia baja?"},
}

ROUTING_HISTORY = "/opt/ai-lab/runtime/state/routing_history.jsonl"

def last_routing_entry():
    if not os.path.exists(ROUTING_HISTORY):
        return {}
    try:
        with open(ROUTING_HISTORY) as f:
            lines = f.readlines()
        for line in reversed(lines):
            line = line.strip()
            if line:
                return json.loads(line)
    except Exception:
        pass
    return {}


def measure(name: str, prompt: str) -> dict:
    payload = json.dumps({
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    })

    t0 = time.time()
    result = subprocess.run(
        ["curl", "-s", "--max-time", "300",
         "-X", "POST", "http://localhost:8083/chat/completions",
         "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True, timeout=300,
    )
    total = time.time() - t0

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"error": "no JSON", "raw": result.stdout[:200], "total": round(total, 2)}

    routing = last_routing_entry()
    first = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    return {
        "model": data.get("model", "?"),
        "total_tokens": data.get("usage", {}).get("total_tokens", "?"),
        "prompt_tokens": data.get("usage", {}).get("prompt_tokens", "?"),
        "completion_tokens": data.get("usage", {}).get("completion_tokens", "?"),
        "total_seconds": round(total, 2),
        "latency_ms": round(total * 1000),
        "ctx_budget": LM_STUDIO_MAX_CONTEXT,
        "first_line": first.split("\n")[0][:80] if first else "(empty)",
        "error": None,
    }


def main():
    print("=" * 70)
    print("LATENCY BASELINE — 3 profiles × 3 samples")
    print(f"Max context: {LM_STUDIO_MAX_CONTEXT}")
    print("=" * 70)

    all_results = {}

    for profile, cfg in PROFILES.items():
        print(f"\n{'─' * 70}")
        print(f"PROFILE: {profile}")
        print(f"Prompt: {cfg['prompt'][:60]}...")
        print(f"{'─' * 70}")
        samples = []
        for i in range(3):
            print(f"  Sample {i+1}/3...", end=" ", flush=True)
            result = measure(profile, cfg["prompt"])
            samples.append(result)
            if result.get("error"):
                print(f"ERROR: {result['error']}")
            else:
                print(f"model={result['model']}  "
                      f"total={result['total_seconds']}s  "
                      f"tokens={result['total_tokens']}  "
                      f"lat={result['latency_ms']}ms")
        all_results[profile] = samples

    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")
    print(f"{'Profile':<12} {'Model':<28} {'Avg(s)':<8} {'Min(s)':<8} {'Max(s)':<8} {'AvgTok':<8}")
    print(f"{'─' * 72}")
    for profile, samples in all_results.items():
        models = set(s.get("model", "?") for s in samples)
        times = [s["total_seconds"] for s in samples if not s.get("error")]
        toks = [s["total_tokens"] for s in samples if not s.get("error")]
        avg_t = sum(times) / len(times) if times else 0
        min_t = min(times) if times else 0
        max_t = max(times) if times else 0
        avg_tok = sum(toks) / len(toks) if toks else 0
        model_str = ", ".join(sorted(models))[:28]
        print(f"{profile:<12} {model_str:<28} {avg_t:<8.1f} {min_t:<8.1f} {max_t:<8.1f} {avg_tok:<8.0f}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
