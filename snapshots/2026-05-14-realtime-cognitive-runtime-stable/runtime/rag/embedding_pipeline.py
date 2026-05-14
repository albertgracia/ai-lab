import json
from pathlib import Path

from runtime.rag.embedder import embed_text

ROOT = Path("/opt/ai-lab")

SUPPORTED_EXTENSIONS = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
}

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".cache",
    "coverage",
    "snapshots",
    ".astro",
}

EXCLUDED_FILES = {
    "package-lock.json",
    "package.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "embedding_records.json",
    "system_snapshot.json",
}

MAX_FILE_SIZE_MB = 2
CHUNK_SIZE = 1200

OUTPUT_FILE = ROOT / "runtime/state/embedding_records.json"
TMP_OUTPUT_FILE = ROOT / "runtime/state/embedding_records.tmp.json"

records = []


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE):
    return [
        text[i:i + chunk_size]
        for i in range(0, len(text), chunk_size)
    ]


def should_skip(path: Path) -> bool:
    if any(part in EXCLUDED_DIRS for part in path.parts):
        return True

    if path.name in EXCLUDED_FILES:
        return True

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return True

    try:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            print(f"SKIPPED LARGE FILE: {path}")
            return True
    except Exception:
        return True

    return False


def process_file(path: Path):
    print(f"\nINDEXING: {path}")

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        if not content.strip():
            print("SKIPPED EMPTY")
            return

        chunks = chunk_text(content)

        print(f"CHUNKS: {len(chunks)}")

        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue

            embedding = embed_text(chunk)

            records.append({
                "file": str(path),
                "chunk": idx,
                "text": chunk,
                "embedding": embedding,
            })

        print(f"OK: {path}")

    except Exception as e:
        print(f"ERROR: {path}: {e}")


def main():
    files = []

    for ext in SUPPORTED_EXTENSIONS:
        files.extend(ROOT.rglob(f"*{ext}"))

    files = sorted(set(files))

    print(f"FILES DISCOVERED: {len(files)}")

    indexed = 0
    skipped = 0

    for path in files:
        if not path.is_file():
            continue

        if should_skip(path):
            skipped += 1
            continue

        indexed += 1
        process_file(path)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(TMP_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f)

    TMP_OUTPUT_FILE.replace(OUTPUT_FILE)

    print("\n====================")
    print(f"FILES INDEXED: {indexed}")
    print(f"FILES SKIPPED: {skipped}")
    print(f"TOTAL RECORDS: {len(records)}")
    print(f"SAVED: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
