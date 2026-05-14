from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient

QDRANT_URL = "http://localhost:6333"
COLLECTION = "ai_lab_memory"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(url=QDRANT_URL)


def search_memory(query: str, limit: int = 3):
    embedding = model.encode(query).tolist()

    results = client.query_points(
        collection_name=COLLECTION,
        query=embedding,
        limit=limit,
        with_payload=True,
    ).points

    return [
        {
            "score": r.score,
            "path": r.payload.get("path"),
            "content": r.payload.get("content"),
            "type": r.payload.get("type"),
        }
        for r in results
    ]


if __name__ == "__main__":
    query = input("Memory Query: ")
    results = search_memory(query)

    for r in results:
        print("=" * 80)
        print(f"score: {r['score']:.4f}")
        print(f"path: {r['path']}")
        print("-" * 80)
        print(r["content"][:700])
