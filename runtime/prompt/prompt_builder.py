import sys
import requests

from runtime.memory.search_memory import search_memory


QDRANT_URL = "http://localhost:6333"
COLLECTION = "agent_knowledge"

EMBEDDING_URL = "http://192.168.1.200:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

TOP_K = 8


def embed(text: str):
    r = requests.post(
        EMBEDDING_URL,
        json={
            "model": EMBEDDING_MODEL,
            "input": text[:8000],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]


def search(query: str):
    vector = embed(query)

    r = requests.post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        json={
            "vector": vector,
            "limit": TOP_K,
            "with_payload": True,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["result"]


def rank_bonus(path: str) -> float:
    bonus = 0.0

    if path.startswith("agents/"):
        bonus += 0.06
    if path.startswith("workflows/"):
        bonus += 0.05
    if path.startswith("rules/"):
        bonus += 0.04
    if path.endswith("SKILL.md"):
        bonus += 0.08
    if "mobile" in path.lower():
        bonus -= 0.05

    return bonus


def build_prompt(user_request: str, results):
    memory_results = search_memory(user_request, limit=3)

    memory_blocks = []
    for memory in memory_results:
        memory_blocks.append(
            f"""### Memory: {memory["path"]}
Score: {memory["score"]:.4f}

{memory["content"][:1200]}
"""
        )

    memory_context = "\n\n".join(memory_blocks)

    enriched = []

    for item in results:
        payload = item.get("payload", {})
        path = payload.get("path", "")
        score = item.get("score", 0)
        adjusted_score = score + rank_bonus(path)

        enriched.append(
            {
                "path": path,
                "type": payload.get("type"),
                "score": score,
                "adjusted_score": adjusted_score,
                "content": payload.get("content", ""),
            }
        )

    enriched.sort(key=lambda x: x["adjusted_score"], reverse=True)

    context_blocks = []

    for item in enriched[:5]:
        context_blocks.append(
            f"""### Source: {item["path"]}
Type: {item["type"]}
Score: {item["score"]:.4f}
Adjusted Score: {item["adjusted_score"]:.4f}

{item["content"][:1800]}
"""
        )

    context = "\n\n".join(context_blocks)

    prompt = f"""# AI Lab Agent Runtime Prompt

You are operating inside Albert's local AI Lab.

You must use the provided persistent memory, agent knowledge, skills, workflows and rules as operational context.

## User Request

{user_request}

## Retrieved Persistent Memory

{memory_context}

## Retrieved Agent Context

{context}

## Instructions

1. Identify the best agent role for this request.
2. Identify relevant skills.
3. Identify whether a workflow applies.
4. Use persistent memory to maintain continuity with previous architecture decisions.
5. Produce a careful technical answer.
6. If commands are needed, prefer safe read-only commands first.
7. Do not suggest destructive commands without explicit confirmation.
8. Explain assumptions clearly.
9. Prioritize local-first, modular, safe and Git-tracked changes.

## Response
"""

    return prompt


def main():
    if len(sys.argv) < 2:
        print('Uso: python3 prompt_builder.py "consulta"')
        sys.exit(1)

    user_request = " ".join(sys.argv[1:])
    results = search(user_request)
    prompt = build_prompt(user_request, results)

    print(prompt)


if __name__ == "__main__":
    main()
