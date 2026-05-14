from sentence_transformers import SentenceTransformer

print("LOADING EMBEDDING MODEL...")

MODEL = SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1.5"
)

print("EMBEDDING MODEL READY")


def embed_text(text: str) -> list[float]:
    """
    Genera embeddings locales.
    """
    return MODEL.encode(text).tolist()
