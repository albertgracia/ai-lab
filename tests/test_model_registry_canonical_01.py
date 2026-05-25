"""MODEL-REGISTRY-CANONICAL-01 tests.

Focus: deterministic canonicalization and bounded helpers.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.gateway.runtime_api_routes import handle_model_registry_routes
from runtime.models.model_registry import (
    DEPRECATED_QWEN_14B_ALIAS,
    MODEL_LLAMA_8B,
    MODEL_NOMIC_EMBED,
    MODEL_QWEN_14B,
    MODEL_QWEN3_VL_8B,
    build_public_registry_snapshot,
    get_model_role,
    get_preferred_model_for_role,
    get_routable_models,
    is_deprecated_model,
    normalize_model_id,
)


class _FakeHandler:
    def __init__(self, path: str):
        self.path = path
        self.sent = None

    def _send_json(self, code: int, payload: dict):
        self.sent = (code, payload)


def test_normalize_model_id_canonicalizes_tolerated_alias():
    assert normalize_model_id("qwen2.5-coder-14b-instruct") == MODEL_QWEN_14B
    assert normalize_model_id("qwen/qwen2.5-coder-14b-instruct") == MODEL_QWEN_14B


def test_deprecated_alias_detected_and_normalizes_to_canonical():
    assert is_deprecated_model(DEPRECATED_QWEN_14B_ALIAS) is True
    assert normalize_model_id(DEPRECATED_QWEN_14B_ALIAS) == MODEL_QWEN_14B


def test_role_lookup_and_preferred_model_for_role():
    assert get_model_role(MODEL_LLAMA_8B) == "FASTPATH"
    assert get_model_role(MODEL_QWEN_14B) == "CODER"
    assert get_model_role(MODEL_NOMIC_EMBED) == "EMBEDDING"
    assert get_preferred_model_for_role("CODER") == MODEL_QWEN_14B
    assert get_preferred_model_for_role("FASTPATH") == MODEL_QWEN3_VL_8B


def test_routable_filter_is_deterministic_and_excludes_embeddings():
    routable = get_routable_models()
    assert routable == sorted(routable)
    assert MODEL_NOMIC_EMBED not in routable
    assert MODEL_LLAMA_8B not in routable
    assert MODEL_QWEN_14B in routable


def test_registry_snapshot_is_deterministic_and_bounded():
    snap = build_public_registry_snapshot()
    assert snap["contract_version"] == "MODEL-REGISTRY-CANONICAL-01"
    assert snap["total"] >= 3
    # stable ordering
    ids = [m["canonical_id"] for m in snap["canonical_models"]]
    assert ids == sorted(ids)


def test_registry_endpoint_returns_snapshot():
    h = _FakeHandler("/runtime/models/registry")
    assert handle_model_registry_routes(h) is True
    code, payload = h.sent
    assert code == 200
    assert payload["status"] in {"ok", "degraded"}
    assert payload["contract_version"] == "MODEL-REGISTRY-CANONICAL-01"
    assert "registry" in payload
