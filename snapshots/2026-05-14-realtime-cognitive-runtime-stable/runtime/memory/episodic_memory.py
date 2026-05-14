import json
import time
from pathlib import Path
from typing import Any


EPISODIC_MEMORY_FILE = Path(
    "/opt/ai-lab/runtime/state/episodic_memory.jsonl"
)


def write_episode(
    event_type: str,
    summary: str,
    payload: dict[str, Any] | None = None,
):
    EPISODIC_MEMORY_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    episode = {
        "timestamp": int(time.time()),
        "event_type": event_type,
        "summary": summary,
        "payload": payload or {},
    }

    with open(
        EPISODIC_MEMORY_FILE,
        "a",
        encoding="utf-8",
    ) as f:
        f.write(
            json.dumps(
                episode,
                ensure_ascii=False,
            )
            + "\n"
        )

    return episode


def read_episodes(
    limit: int = 10,
):
    if not EPISODIC_MEMORY_FILE.exists():
        return []

    lines = EPISODIC_MEMORY_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    episodes = []

    for line in lines[-limit:]:
        try:
            episodes.append(json.loads(line))
        except Exception:
            continue

    return episodes


def search_episodes(
    query: str,
    limit: int = 10,
):
    if not EPISODIC_MEMORY_FILE.exists():
        return []

    query_lower = query.lower()

    matches = []

    lines = EPISODIC_MEMORY_FILE.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    for line in reversed(lines):
        try:
            episode = json.loads(line)
        except Exception:
            continue

        haystack = json.dumps(
            episode,
            ensure_ascii=False,
        ).lower()

        if query_lower in haystack:
            matches.append(episode)

        if len(matches) >= limit:
            break

    return matches


if __name__ == "__main__":
    write_episode(
        event_type="episodic_memory_test",
        summary="Episodic memory initialized successfully.",
        payload={
            "component": "runtime.memory.episodic_memory",
            "status": "ok",
        },
    )

    print("LAST EPISODES")
    print("=============")

    for episode in read_episodes(limit=5):
        print(episode)
