import pytest

from runtime.router.model_policy import (
    PRIMARY_OPERATIONAL_MODEL,
    PRIMARY_CODING_MODEL,
    DEPRECATED_MODEL_IDS,
    is_operational_prompt,
    is_coding_prompt,
    is_runtime_grounded_prompt,
    is_deprecated_model,
    resolve_operational_model,
    resolve_coding_model,
    validate_model_selection,
)
from runtime.state.lmstudio_state import (
    normalize_model_id,
    _DEPRECATED_PREFIXES,
)


class TestModelPolicyDetection:
    def test_model_policy_detects_operational_prompt(self):
        assert is_operational_prompt("estado GPU RX9070")
        assert is_operational_prompt("estado runtime AI-LAB")
        assert is_operational_prompt("qué confianza tienen los sensores")
        assert is_operational_prompt("health del gateway")
        assert is_operational_prompt("topology del cluster")
        assert is_operational_prompt("storage backup status")
        assert not is_operational_prompt("implementa un parser async")
        assert not is_operational_prompt("refactoriza esta función")

    def test_model_policy_detects_coding_prompt(self):
        assert is_coding_prompt("implementa un parser async para Prometheus")
        assert is_coding_prompt("refactoriza esta clase")
        assert is_coding_prompt("corrige el bug en el router")
        assert is_coding_prompt("genera tests pytest para cognitive_summary")
        assert is_coding_prompt("analiza este stacktrace")
        assert is_coding_prompt("escribe código para el endpoint")
        assert is_coding_prompt("debugging del middleware")
        assert not is_coding_prompt("estado GPU RX9070")


class TestOperationalRouting:
    def test_operational_prompt_routes_to_llama(self):
        result = validate_model_selection(
            task_type="general",
            model_id="qwen2.5-coder-14b-instruct",
            route_family="minimal",
            user_text="estado GPU RX9070",
        )
        assert result == PRIMARY_OPERATIONAL_MODEL

    def test_runtime_state_prompt_uses_llama(self):
        result = validate_model_selection(
            task_type="general",
            model_id="qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            user_text="cómo está el runtime de AI-LAB",
        )
        assert result == PRIMARY_OPERATIONAL_MODEL


class TestCodingRouting:
    def test_coding_prompt_routes_to_qwen(self):
        result = validate_model_selection(
            task_type="coding",
            model_id="llama-3.1-8b-instruct",
            route_family="cognitive",
            user_text="implementa un parser async para Prometheus",
        )
        assert result == PRIMARY_CODING_MODEL

    def test_architecture_prompt_uses_qwen(self):
        result = validate_model_selection(
            task_type="reasoning",
            model_id="llama-3.1-8b-instruct",
            route_family="cognitive",
            user_text="arquitectura del nuevo router distribuido",
        )
        assert result == PRIMARY_CODING_MODEL


class TestDeprecatedModel:
    def test_deprecated_model_not_selected_for_runtime(self):
        assert is_deprecated_model("lmstudio-community/qwen2.5-coder-14b-instruct")

    def test_gpu_prompt_never_uses_deprecated_model(self):
        result = validate_model_selection(
            task_type="general",
            model_id="lmstudio-community/qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            user_text="estado GPU RX9070",
        )
        assert result != "lmstudio-community/qwen2.5-coder-14b-instruct"
        assert result == PRIMARY_OPERATIONAL_MODEL

    def test_fallback_chain_excludes_deprecated_model(self):
        result = validate_model_selection(
            task_type="general",
            model_id="lmstudio-community/qwen2.5-coder-14b-instruct",
            route_family="minimal",
            user_text="hola",
        )
        assert result != "lmstudio-community/qwen2.5-coder-14b-instruct"
        assert result == PRIMARY_OPERATIONAL_MODEL


class TestDeprecatedInventory:
    def test_deprecated_model_marked_hidden(self):
        normalized = normalize_model_id("lmstudio-community/qwen2.5-coder-14b-instruct")
        assert normalized == "qwen2.5-coder-14b-instruct"
        # The prefix is in _DEPRECATED_PREFIXES
        assert any("lmstudio-community/qwen2.5-coder-14b-instruct" == p for p in _DEPRECATED_PREFIXES)

    def test_operational_inventory_excludes_deprecated_model(self):
        from runtime.state.lmstudio_state import ModelStatusTracker, _DEPRECATED_PREFIXES
        tracker = ModelStatusTracker()
        assert len(_DEPRECATED_PREFIXES) > 0
        for prefix in _DEPRECATED_PREFIXES:
            assert prefix.startswith("lmstudio-community/")


class TestResolveHelpers:
    def test_runtime_grounded_prompt_uses_operational_model(self):
        assert is_runtime_grounded_prompt("estado GPU")
        assert is_runtime_grounded_prompt("qué está pasando en el runtime")
        assert is_runtime_grounded_prompt("resumen operacional")
        assert not is_runtime_grounded_prompt("implementa tests para pytest")

    def test_resolve_helpers_return_expected_models(self):
        assert resolve_operational_model() == "llama-3.1-8b-instruct"
        assert resolve_coding_model() == "qwen/qwen2.5-coder-14b-instruct"
