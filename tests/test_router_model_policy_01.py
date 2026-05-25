"""
ROUTER-HF-MODEL-POLICY-01: Canonical Router Model Policy Tests.

Validates:
- llama no routable
- llama not selected in any route
- fast/observe/minimal/fallback/degraded -> qwen3-vl-8b-instruct
- coding/reasoning/tool-use/deep/architecture -> qwen/qwen2.5-coder-14b-instruct
- registry contains qwen3-vl
- registry marks llama quarantined
- no hardcoded llama active in gateway/router/profile fallbacks
"""

import sys
import os
sys.path.insert(0, '/opt/ai-lab')

from runtime.models.model_policy import (
    CANONICAL_MODELS,
    PROHIBITED_MODELS,
    FAST_MODEL,
    STRONG_MODEL,
    get_model_for_route,
    get_fast_model,
    get_fallback_model,
    get_degraded_model,
    get_coding_model,
    get_reasoning_model,
    get_tool_use_model,
    is_prohibited_model,
    validate_route_model_selection,
)

from runtime.models.model_registry import (
    MODEL_QWEN3_VL_8B,
    MODEL_LLAMA_8B,
    _DESCRIPTOR_BY_CANONICAL,
)

PROHIBITED = "llama-3.1-8b-instruct"

# ── model_policy tests ─────────────────────────────────────────────────

def test_fast_model():
    assert get_fast_model() == FAST_MODEL
    assert get_model_for_route("fast") == FAST_MODEL
    print("  OK: fast => qwen3-vl-8b-instruct")


def test_observe_model():
    assert get_model_for_route("observe") == FAST_MODEL
    print("  OK: observe => qwen3-vl-8b-instruct")


def test_minimal_model():
    assert get_model_for_route("minimal") == FAST_MODEL
    print("  OK: minimal => qwen3-vl-8b-instruct")


def test_fallback_model():
    assert get_fallback_model() == FAST_MODEL
    assert get_model_for_route("fallback") == FAST_MODEL
    print("  OK: fallback => qwen3-vl-8b-instruct")


def test_degraded_model():
    assert get_degraded_model() == FAST_MODEL
    assert get_model_for_route("degraded") == FAST_MODEL
    print("  OK: degraded => qwen3-vl-8b-instruct")


def test_greeting_model():
    assert get_model_for_route("greeting") == FAST_MODEL
    print("  OK: greeting => qwen3-vl-8b-instruct")


def test_lightweight_model():
    assert get_model_for_route("lightweight") == FAST_MODEL
    print("  OK: lightweight => qwen3-vl-8b-instruct")


def test_coding_model():
    assert get_coding_model() == STRONG_MODEL
    assert get_model_for_route("coding") == STRONG_MODEL
    print("  OK: coding => qwen/qwen2.5-coder-14b-instruct")


def test_reasoning_model():
    assert get_reasoning_model() == STRONG_MODEL
    assert get_model_for_route("reasoning") == STRONG_MODEL
    print("  OK: reasoning => qwen/qwen2.5-coder-14b-instruct")


def test_tool_use_model():
    assert get_tool_use_model() == STRONG_MODEL
    assert get_model_for_route("tool-use") == STRONG_MODEL
    print("  OK: tool-use => qwen/qwen2.5-coder-14b-instruct")


def test_auto_model():
    assert get_model_for_route("auto") == STRONG_MODEL
    print("  OK: auto => qwen/qwen2.5-coder-14b-instruct")


def test_architecture_model():
    assert get_model_for_route("architecture") == STRONG_MODEL
    print("  OK: architecture => qwen/qwen2.5-coder-14b-instruct")


def test_report_model():
    assert get_model_for_route("report") == STRONG_MODEL
    print("  OK: report => qwen/qwen2.5-coder-14b-instruct")


def test_unknown_route_falls_back():
    assert get_model_for_route("nonexistent") == FAST_MODEL
    print("  OK: unknown route falls back to fast model")


# ── prohibited model tests ─────────────────────────────────────────────

def test_llama_is_prohibited():
    assert is_prohibited_model(PROHIBITED)
    print("  OK: llama-3.1-8b-instruct is prohibited")


def test_qwen_not_prohibited():
    assert not is_prohibited_model(FAST_MODEL)
    assert not is_prohibited_model(STRONG_MODEL)
    print("  OK: qwen models are not prohibited")


def test_none_not_prohibited():
    assert not is_prohibited_model(None)
    assert not is_prohibited_model("")
    print("  OK: None/empty not prohibited")


def test_prohibited_models_set():
    assert PROHIBITED in PROHIBITED_MODELS
    assert len(PROHIBITED_MODELS) == 1
    print("  OK: PROHIBITED_MODELS contains only llama")


# ── validate_route_model_selection tests ───────────────────────────────

def test_validate_prohibited_fast_route():
    result = validate_route_model_selection(PROHIBITED, route="fast")
    assert result == FAST_MODEL
    print("  OK: validate prohibited llama fast route => qwen3-vl-8b-instruct")


def test_validate_prohibited_coding_route():
    result = validate_route_model_selection(PROHIBITED, route="coding")
    assert result == STRONG_MODEL
    print("  OK: validate prohibited llama coding route => qwen/qwen2.5-coder-14b-instruct")


def test_validate_allowed_model_passes():
    result = validate_route_model_selection(FAST_MODEL, route="coding")
    assert result == FAST_MODEL
    print("  OK: validate allowed model passes through unchanged")


# ── canonical models completeness ──────────────────────────────────────

def test_canonical_models_completeness():
    required = [
        "fast", "observe", "minimal", "fallback", "degraded",
        "greeting", "lightweight", "auto", "coding", "reasoning",
        "tool-use", "architecture", "report",
    ]
    for route in required:
        assert route in CANONICAL_MODELS, f"Missing: {route}"
    print(f"  OK: All {len(required)} required routes present")


def test_no_llama_in_canonical_values():
    for route, model in CANONICAL_MODELS.items():
        assert "llama" not in model.lower(), f"Route {route} has llama: {model}"
    print("  OK: No llama in any CANONICAL_MODELS value")


# ── model_registry tests ───────────────────────────────────────────────

def test_registry_has_qwen3_vl():
    assert MODEL_QWEN3_VL_8B == "qwen3-vl-8b-instruct"
    print(f"  OK: MODEL_QWEN3_VL_8B = {MODEL_QWEN3_VL_8B}")


def test_registry_llama_is_quarantined():
    desc = _DESCRIPTOR_BY_CANONICAL.get(MODEL_LLAMA_8B)
    assert desc is not None, "llama descriptor not found"
    assert desc.routable == False, "llama must not be routable"
    assert desc.status == "quarantined", f"llama status must be quarantined, got {desc.status}"
    print("  OK: llama descriptor is routable=False, status=quarantined")


def test_llama_not_routable():
    routable = [m.canonical_id for m in _DESCRIPTOR_BY_CANONICAL.values() if m.routable]
    assert MODEL_LLAMA_8B not in routable, "llama must not be in routable list"
    print("  OK: llama not in routable models list")


def test_qwen3_vl_is_routable():
    desc = _DESCRIPTOR_BY_CANONICAL.get(MODEL_QWEN3_VL_8B)
    assert desc is not None, "qwen3-vl descriptor not found"
    assert desc.routable == True, "qwen3-vl must be routable"
    print("  OK: qwen3-vl-8b-instruct is routable")


def test_qwen14b_is_routable():
    from runtime.models.model_registry import MODEL_QWEN_14B
    desc = _DESCRIPTOR_BY_CANONICAL.get(MODEL_QWEN_14B)
    assert desc is not None
    assert desc.routable == True
    print("  OK: qwen/qwen2.5-coder-14b-instruct is routable")


def test_routable_models_count():
    routable = [m.canonical_id for m in _DESCRIPTOR_BY_CANONICAL.values() if m.routable]
    assert len(routable) >= 2, f"Expected at least 2 routable models, got {len(routable)}"
    print(f"  OK: {len(routable)} routable models (qwen3-vl + qwen14b + ...)")


def test_qwen3_vl_not_prohibited():
    assert not is_prohibited_model("qwen3-vl-8b-instruct")
    print("  OK: qwen3-vl-8b-instruct is NOT in PROHIBITED_MODELS")


# ── runner ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        ("fast", test_fast_model),
        ("observe", test_observe_model),
        ("minimal", test_minimal_model),
        ("fallback", test_fallback_model),
        ("degraded", test_degraded_model),
        ("greeting", test_greeting_model),
        ("lightweight", test_lightweight_model),
        ("coding", test_coding_model),
        ("reasoning", test_reasoning_model),
        ("tool-use", test_tool_use_model),
        ("auto", test_auto_model),
        ("architecture", test_architecture_model),
        ("report", test_report_model),
        ("unknown route fallback", test_unknown_route_falls_back),
        ("llama prohibited", test_llama_is_prohibited),
        ("qwen not prohibited", test_qwen_not_prohibited),
        ("none not prohibited", test_none_not_prohibited),
        ("prohibited set", test_prohibited_models_set),
        ("validate prohibited fast", test_validate_prohibited_fast_route),
        ("validate prohibited coding", test_validate_prohibited_coding_route),
        ("validate allowed pass", test_validate_allowed_model_passes),
        ("canonical completeness", test_canonical_models_completeness),
        ("no llama in values", test_no_llama_in_canonical_values),
        ("registry has qwen3-vl", test_registry_has_qwen3_vl),
        ("registry llama quarantined", test_registry_llama_is_quarantined),
        ("llama not routable", test_llama_not_routable),
        ("qwen3-vl routable", test_qwen3_vl_is_routable),
        ("qwen14b routable", test_qwen14b_is_routable),
        ("routable count", test_routable_models_count),
        ("qwen3-vl not prohibited", test_qwen3_vl_not_prohibited),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"  FAIL: {name}: {e}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
    print("ALL TESTS PASSED!")
