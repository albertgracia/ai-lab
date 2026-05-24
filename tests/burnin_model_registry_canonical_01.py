"""MODEL-REGISTRY-CANONICAL-01 burn-in.

Run:
  python3 tests/burnin_model_registry_canonical_01.py
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS,
    MODEL_LLAMA_8B,
    MODEL_QWEN_14B,
    build_public_registry_snapshot,
    is_deprecated_model,
    normalize_model_id,
)


def main() -> int:
    snap = build_public_registry_snapshot()
    print(json.dumps(snap, indent=2, sort_keys=True))

    # Basic invariants
    if normalize_model_id("qwen2.5-coder-14b-instruct") != MODEL_QWEN_14B:
        raise SystemExit("burnin_normalize_tolerated_alias_failed")
    if not is_deprecated_model(DEPRECATED_QWEN_14B_ALIAS):
        raise SystemExit("burnin_deprecated_detection_failed")
    if normalize_model_id(DEPRECATED_QWEN_14B_ALIAS) != MODEL_QWEN_14B:
        raise SystemExit("burnin_deprecated_normalize_failed")
    if MODEL_LLAMA_8B not in [m["canonical_id"] for m in snap.get("canonical_models", [])]:
        raise SystemExit("burnin_missing_llama")

    print("OK burnin model registry canonical 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
