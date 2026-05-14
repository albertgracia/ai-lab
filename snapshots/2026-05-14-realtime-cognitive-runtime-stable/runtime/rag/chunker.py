from pathlib import Path
from dataclasses import dataclass

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 120


@dataclass
class Chunk:
    source: str
    chunk_id: str
    content: str
    start: int
    end: int


def split_text(text: str):
    chunks = []

    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE

        chunk = text[start:end]

        chunks.append(
            (
                start,
                min(end, len(text)),
                chunk
            )
        )

        start += CHUNK_SIZE - CHUNK_OVERLAP

    return chunks


def chunk_file(path: Path):
    text = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    results = []

    for idx, (start, end, content) in enumerate(
        split_text(text)
    ):
        results.append(
            Chunk(
                source=str(path),
                chunk_id=f"{path.name}-{idx}",
                content=content,
                start=start,
                end=end
            )
        )

    return results


if __name__ == "__main__":
    path = Path("/opt/ai-lab/OPENCODE.md")

    chunks = chunk_file(path)

    print(f"chunks: {len(chunks)}")

    for c in chunks[:3]:
        print("\n================")
        print(c.chunk_id)
        print(c.content[:200])
