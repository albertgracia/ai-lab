import sys
import requests

QDRANT_URL = "http://localhost:6333"
COLLECTION = "agent_knowledge"

EMBEDDING_URL = "http://192.168.1.200:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

TOP_K = 5


def embed(text: str):
    r = requests.post(
        EMBEDDING_URL,
        json={
            "model": EMBEDDING_MODEL,
            "input": text[:8000]
        },
        timeout=60
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
            "with_payload": True
        },
        timeout=60
    )
    r.raise_for_status()
    return r.json()["result"]


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 search_agent.py \"consulta\"")
        sys.exit(1)

    query = " ".join(sys.argv[1:])
    results = search(query)

    print(f"\nQuery: {query}\n")
    print("=" * 80)

    for i, item in enumerate(results, 1):
        payload = item.get("payload", {})
        score = item.get("score")

        print(f"\n[{i}] score={score:.4f}")
        print(f"path: {payload.get('path')}")
        print(f"type: {payload.get('type')}")
        print("-" * 80)
        print(payload.get("content", "")[:1200])
        print("=" * 80)


if __name__ == "__main__":
    main()
