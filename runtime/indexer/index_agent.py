import os
import uuid
import requests
from pathlib import Path

AGENT_PATH = Path("/opt/ai-lab/.agent")
QDRANT_URL = "http://localhost:6333"
COLLECTION = "agent_knowledge"

EMBEDDING_URL = "http://192.168.1.200:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

def embed(text):
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

def recreate_collection(vector_size):
    requests.delete(f"{QDRANT_URL}/collections/{COLLECTION}")
    r = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}",
        json={
            "vectors": {
                "size": vector_size,
                "distance": "Cosine"
            }
        }
    )
    r.raise_for_status()

def upsert_point(file_path, content, vector):
    rel_path = str(file_path.relative_to(AGENT_PATH))
    payload = {
        "path": rel_path,
        "type": rel_path.split("/")[0],
        "content": content[:4000]
    }

    point = {
        "id": str(uuid.uuid4()),
        "vector": vector,
        "payload": payload
    }

    r = requests.put(
        f"{QDRANT_URL}/collections/{COLLECTION}/points",
        json={"points": [point]}
    )
    r.raise_for_status()

def main():
    files = [
        p for p in AGENT_PATH.rglob("*")
        if p.is_file()
        and p.suffix.lower() in [".md", ".json", ".txt", ".yaml", ".yml"]
    ]

    print(f"Found {len(files)} files")

    first_text = files[0].read_text(errors="ignore")
    first_vector = embed(first_text)
    recreate_collection(len(first_vector))

    for i, file_path in enumerate(files, 1):
        content = file_path.read_text(errors="ignore").strip()
        if not content:
            continue

        vector = embed(content)
        upsert_point(file_path, content, vector)
        print(f"[{i}/{len(files)}] Indexed {file_path}")

    print("Done")

if __name__ == "__main__":
    main()
