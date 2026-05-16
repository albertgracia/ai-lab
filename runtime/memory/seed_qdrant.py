"""Seed Qdrant from pre-seed JSONL backups.

Usage:
    python3 seed_qdrant.py

Reads routing_history.jsonl and cognitive_history.jsonl from backup,
transforms to current schema, generates embeddings, and upserts to Qdrant.
"""

import json
import os
import sys
import time

BACKUP_DIR = "/opt/ai-lab/backups/pre-qdrant-seed-20260516-133327"

sys.path.insert(0, "/opt/ai-lab")
from runtime.memory.qdrant_store import store_embedding, count_points


def load_jsonl(path: str) -> list[dict]:
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def transform_routing(entry: dict) -> dict:
    entry["schema_version"] = "1.0"
    if entry.get("success"):
        entry["event_type"] = "routing_success"
    elif entry.get("failover"):
        entry["event_type"] = "routing_failover"
    else:
        entry["event_type"] = "routing_error"
    return entry


def transform_cognitive(entry: dict) -> dict:
    entry["schema_version"] = "1.0"
    if entry.get("budget_truncation"):
        entry["event_type"] = "budget_truncation"
    elif entry.get("files_used"):
        entry["event_type"] = "context_shaping"
    else:
        entry["event_type"] = "memory_digest"
    return entry


def seed_collection(name: str, entries: list[dict], transform_fn) -> tuple[int, int]:
    total = len(entries)
    ok = 0
    fail = 0
    for i, entry in enumerate(entries):
        payload = transform_fn(entry)
        try:
            ok_flag = store_embedding(name, payload)
            if ok_flag:
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  [{i+1}/{total}] FAIL: {e}")
            fail += 1

        if (i + 1) % 10 == 0 or i == total - 1:
            print(f"  [{i+1}/{total}] ok={ok} fail={fail}")
    return ok, fail


def main():
    print("=" * 55)
    print("Qdrant Seed — Pre-seed JSONL → Qdrant")
    print("=" * 55)

    # ── routing_history ──
    routing_path = os.path.join(BACKUP_DIR, "routing_history.jsonl")
    routing = load_jsonl(routing_path)
    print(f"\n📦 routing_history: {len(routing)} entries")
    before_routing = count_points("routing_history")
    print(f"   Qdrant before: {before_routing}")
    t0 = time.time()
    ok_r, fail_r = seed_collection("routing_history", routing, transform_routing)
    after_routing = count_points("routing_history")
    t1 = time.time()
    print(f"   Qdrant after:  {after_routing} ({after_routing - before_routing} new)")
    print(f"   Time: {t1 - t0:.1f}s   OK: {ok_r}   Fail: {fail_r}")

    # ── cognitive_history ──
    cognitive_path = os.path.join(BACKUP_DIR, "cognitive_history.jsonl")
    cognitive = load_jsonl(cognitive_path)
    print(f"\n📦 cognitive_history: {len(cognitive)} entries")
    before_cog = count_points("cognitive_history")
    print(f"   Qdrant before: {before_cog}")
    t2 = time.time()
    ok_c, fail_c = seed_collection("cognitive_history", cognitive, transform_cognitive)
    after_cog = count_points("cognitive_history")
    t3 = time.time()
    print(f"   Qdrant after:  {after_cog} ({after_cog - before_cog} new)")
    print(f"   Time: {t3 - t2:.1f}s   OK: {ok_c}   Fail: {fail_c}")

    # ── summary ──
    print(f"\n{'=' * 55}")
    print(f"Total OK:  {ok_r + ok_c}")
    print(f"Total Fail: {fail_r + fail_c}")
    print(f"Total Time: {t3 - t0:.1f}s")
    print(f"Routing:  {count_points('routing_history')} points")
    print(f"Cognitive: {count_points('cognitive_history')} points")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
