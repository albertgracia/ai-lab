from pathlib import Path
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import uuid

QDRANT_URL = "http://localhost:6333"
COLLECTION = "ai_lab_memory"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = QdrantClient(url=QDRANT_URL)

memory_path = Path("/opt/ai-lab/memory")


def ensure_collection(vector_size: int):
    collections = client.get_collections().collections
    names = [c.name for c in collections]

    if COLLECTION not in names:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        print(f"Created collection: {COLLECTION}")


files = list(memory_path.rglob("*.md"))
points = []

if not files:
    print("No memory files found.")
    raise SystemExit(0)

first_content = files[0].read_text(encoding="utf-8")
first_embedding = model.encode(first_content).tolist()

ensure_collection(len(first_embedding))

for file in files:
    try:
        content = file.read_text(encoding="utf-8")
        embedding = model.encode(content).tolist()

        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "path": str(file.relative_to(memory_path)),
                    "content": content,
                    "type": "memory"
                }
            )
        )

        print(f"Indexed: {file}")

    except Exception as e:
        print(f"ERROR: {file} -> {e}")

if points:
    client.upsert(
        collection_name=COLLECTION,
        points=points
    )

    print(f"\nIndexed {len(points)} memory files.")