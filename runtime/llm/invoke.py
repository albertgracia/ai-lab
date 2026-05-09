import sys
from pathlib import Path

import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))

from runtime.llm.model_router import select_node
from runtime.state.system_state import build_system_state


SYSTEM_PROMPT = """
Eres el runtime cognitivo local de AI-LAB.
Responde siempre en español.
Usa el estado real del sistema como fuente de verdad.
Distingue hechos de hipótesis.
No propongas cambios destructivos sin confirmación explícita.
Sé claro, técnico y accionable.
"""


def call_lmstudio(node, user_prompt: str):
    url = f"http://{node['host']}:{node['port']}/v1/chat/completions"

    payload = {
        "model": node["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1800,
    }

    response = requests.post(url, json=payload, timeout=300)

    if response.status_code >= 400:
        print("ERROR LM Studio:")
        print(response.status_code)
        print(response.text[:2000])
        response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 runtime/llm/invoke.py "petición"')
        sys.exit(1)

    request = " ".join(sys.argv[1:])

    build_system_state()

    node = select_node(request)

    print(f"[N] Selected Inference Node: {node['name']} ({node['host']}:{node['port']})")
    print(f"[N] Selected Model: {node['model']}")
    print(f"[N] Capability: {node['capability']}")
    print(f"[N] Estimated free VRAM: {node['vram_free_gib_estimated']} GiB")
    print("[1] Invoking LLM...\n")

    snapshot_path = Path("/opt/ai-lab/runtime/state/system_snapshot.json")

    snapshot = (
        snapshot_path.read_text(errors="ignore")
        if snapshot_path.exists()
        else "{}"
    )

    grounded_request = f"""
Responde usando SOLO el siguiente estado real del AI-LAB.

NO inventes:
- métricas
- servicios
- módulos
- porcentajes
- latencias
- capacidades
- estados operativos

Si algo no aparece en el estado, di:
"no consta en el estado actual".

## ESTADO REAL

{snapshot}

## PETICIÓN

{request}
"""

    answer = call_lmstudio(node, grounded_request)

    print("=" * 80)
    print(answer)
    print("=" * 80)


if __name__ == "__main__":
    main()
