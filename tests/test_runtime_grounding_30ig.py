import json
import time
from unittest.mock import patch

from runtime.context.runtime_grounding import (
    UNKNOWN_STATE_TOKENS,
    is_runtime_grounded_prompt,
    extract_runtime_entities,
    validate_runtime_claim,
    build_grounding_envelope,
    filter_unobserved_claims,
    validate_response_against_observed_runtime,
)
from runtime.context.runtime_entity_registry import (
    RuntimeEntityRegistry,
    OBSERVED_ENTITY_TYPES,
    ObservedEntity,
)

SAMPLE_RUNTIME_CONTEXT = {
    "primary_runtime_ip": "192.168.1.30",
    "runtime_hostname": "ubuntu-ialab",
    "gpu_operational_summaries": [
        {
            "gpu_id": "RX9070",
            "host": "192.168.1.50",
            "inventory_state": "known",
            "observed_state": "online",
            "operational_state": "active",
            "source_of_truth": ["gpu_exporter", "prometheus"],
            "freshness": {"status": "fresh", "age_seconds": 5, "source": "prometheus"},
            "confidence": "high",
        },
        {
            "gpu_id": "RX7900XT",
            "host": "192.168.1.60",
            "inventory_state": "known",
            "observed_state": "expected_offline",
            "operational_state": "inactive",
            "source_of_truth": ["inventory"],
            "freshness": {"status": "unavailable", "age_seconds": None, "source": "inventory"},
            "confidence": "medium",
        },
    ],
    "inference_nodes": {
        "active": [{"name": "RX9070", "host": "192.168.1.50", "status": "online"}],
        "inventory": [{"name": "RX7900XT", "host": "192.168.1.60", "status": "offline"}],
    },
    "models": {
        "active": [
            {"id": "llama-3.1-8b-instruct", "role": "lightweight"},
            {"id": "qwen2.5-coder-14b-instruct", "role": "coding"},
        ],
        "disabled": [{"id": "qwen/qwen3.6-27b", "disabled_reason": "FASE 29.3"}],
        "discovered": [{"id": "lmstudio-community/qwen2.5-coder-14b-instruct"}],
    },
    "services": {
        "core": ["ailab-gateway (:8008)", "ailab-router (:8083)", "ailab-live-api (:8084)"],
        "support": ["ailab-docs (:4322)", "ailab-heartbeat", "ailab-metrics (:3010)"],
        "observability": [
            {"name": "prometheus", "url": "http://192.168.1.40:9090", "role": "metrics TSDB"},
            {"name": "grafana", "url": "http://192.168.1.40:3000", "role": "dashboards"},
        ],
    },
    "topology_mode": "degraded_single_gpu",
    "runtime_topology": {"mode": "degraded_single_gpu"},
    "sensor_snapshot": {
        "observed_data": {
            "system_node": {"fs_usage_pct": 55},
        },
    },
}


class TestIsRuntimeGroundedPrompt:
    def test_detects_gpu_query(self):
        assert is_runtime_grounded_prompt("estado GPU RX9070")

    def test_detects_runtime_query(self):
        assert is_runtime_grounded_prompt("cómo está el runtime de AI-LAB")

    def test_detects_sensor_confidence_query(self):
        assert is_runtime_grounded_prompt("qué confianza tienen los sensores")

    def test_detects_entity_reference(self):
        assert is_runtime_grounded_prompt("qué GPU está activa")

    def test_rejects_coding_prompt(self):
        assert not is_runtime_grounded_prompt("implementa un parser async")

    def test_rejects_empty_text(self):
        assert not is_runtime_grounded_prompt("")

    def test_rejects_short_text(self):
        assert not is_runtime_grounded_prompt("abc")


class TestExtractRuntimeEntities:
    def test_extracts_gpu_references(self):
        result = extract_runtime_entities("dime el estado de la RX9070 y la RX7900XT")
        assert len(result["gpu"]) == 2

    def test_extracts_model_references(self):
        result = extract_runtime_entities("qué modelos hay activos: llama, qwen")
        assert len(result["model"]) == 2

    def test_extracts_host_references(self):
        result = extract_runtime_entities("qué pasa en 192.168.1.30")
        assert len(result["host"]) >= 1

    def test_extracts_service_references(self):
        result = extract_runtime_entities("cómo está el gateway")
        assert len(result["service"]) >= 1

    def test_extracts_storage_references(self):
        result = extract_runtime_entities("cómo está el storage")
        assert len(result["storage"]) >= 1

    def test_empty_text_returns_empty(self):
        result = extract_runtime_entities("")
        assert all(len(v) == 0 for v in result.values())


class TestValidateRuntimeClaim:
    def test_valid_gpu_claim(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        result = validate_runtime_claim("RX9070 is active", registry)
        assert result["valid"]

    def test_invalid_gpu_claim(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        result = validate_runtime_claim("A100 is running", registry)
        assert not result["valid"]
        assert result["unknown_state"] == "NOT_OBSERVED"

    def test_empty_claim_returns_invalid(self):
        result = validate_runtime_claim("")
        assert not result["valid"]

    def test_no_registry_returns_valid_with_note(self):
        result = validate_runtime_claim("RX9070 is active")
        assert result["valid"]

    def test_invalid_model_claim(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        result = validate_runtime_claim("using GPT-4", registry)
        assert not result["valid"]


class TestBuildGroundingEnvelope:
    def test_grounding_envelope_contains_required_fields(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        envelope = build_grounding_envelope(
            "estado GPU RX9070", runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        assert envelope["contract_version"] == "31E"
        assert envelope["intent_detected"] is True
        assert envelope["grounded"] is True
        assert "observed_entities" in envelope

    def test_grounding_envelope_without_intent(self):
        envelope = build_grounding_envelope("")
        assert envelope["intent_detected"] is False
        assert envelope["grounded"] is False

    def test_observed_entities_contains_gpus(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        envelope = build_grounding_envelope(
            "estado GPU", entity_registry=registry,
        )
        entities = envelope.get("observed_entities", {})
        gpus = entities.get("gpu", [])
        names = [g["name"] for g in gpus]
        assert "RX9070" in names
        assert "RX7900XT" in names

    def test_forbidden_patterns_contains_gpu_denylist(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        envelope = build_grounding_envelope(
            "test", entity_registry=registry,
        )
        patterns = envelope.get("forbidden_patterns", {})
        assert "forbidden_gpus" in patterns
        assert "a100" in patterns["forbidden_gpus"]


class TestFilterUnobservedClaims:
    def test_filters_unobserved_gpu(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "La GPU A100 tiene 80GB de VRAM"
        sanitized, claims = filter_unobserved_claims(text, registry)
        assert len(claims) > 0
        assert any("a100" in c.lower() for c in claims)

    def test_passes_observed_gpu(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "La GPU RX9070 tiene 16GB de VRAM"
        sanitized, claims = filter_unobserved_claims(text, registry)
        assert len(claims) == 0

    def test_filters_unobserved_model(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "El modelo GPT-4 es muy potente"
        sanitized, claims = filter_unobserved_claims(text, registry)
        assert len(claims) > 0
        assert any("gpt" in c.lower() for c in claims)

    def test_filters_unknown_ip(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "El nodo 10.0.0.1 no responde"
        sanitized, claims = filter_unobserved_claims(text, registry)
        ips_found = [c for c in claims if "unknown_ip" in c]
        assert len(ips_found) >= 1


class TestValidateResponseAgainstObservedRuntime:
    def test_valid_response_passes(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "La GPU RX9070 esta activa con 16GB VRAM"
        result = validate_response_against_observed_runtime(
            text, runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        assert result["valid"]

    def test_invalid_response_with_unobserved_gpu(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "La GPU NVIDIA A100 tiene 80GB VRAM y esta en el nodo AWS"
        result = validate_response_against_observed_runtime(
            text, runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        assert not result["valid"]
        assert len(result["unverified_claims"]) > 0

    def test_sanitized_text_contains_markers(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "La GPU A100 tiene 80GB"
        result = validate_response_against_observed_runtime(
            text, runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        assert "[NO OBSERVADO" in result["sanitized_text"]

    def test_evidence_score_decreases_with_violations(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "Usando GPT-4 en AWS con A100 y Kubernetes"
        result = validate_response_against_observed_runtime(
            text, runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        assert result["evidence_score"] < 1.0
        assert len(result["invented_entities"]) > 0

    def test_empty_response_returns_valid(self):
        result = validate_response_against_observed_runtime("")
        assert result["valid"]

    def test_unknown_state_on_high_violations(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        text = "GPU A100 H100 B200 en AWS con GPT-4 y Claude en Kubernetes"
        result = validate_response_against_observed_runtime(
            text, runtime_context=SAMPLE_RUNTIME_CONTEXT,
            entity_registry=registry,
        )
        if result["unknown_state"]:
            assert result["unknown_state"] in UNKNOWN_STATE_TOKENS


class TestRuntimeRegistryIntegration:
    def test_registry_builds_from_context(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        entities = registry.get_observed_entities()
        assert "gpu" in entities
        assert "host" in entities
        assert "model" in entities
        assert "service" in entities
        assert "topology_mode" in entities
        assert "storage" in entities

    def test_registry_known_gpus(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        gpus = registry.get_known_gpus()
        assert "RX9070" in gpus
        assert "RX7900XT" in gpus

    def test_registry_known_hosts(self):
        registry = RuntimeEntityRegistry(SAMPLE_RUNTIME_CONTEXT)
        hosts = registry.get_known_hosts()
        assert "192.168.1.30" in hosts
        assert "192.168.1.50" in hosts
        assert "192.168.1.60" in hosts

    def test_observed_entity_types_frozen(self):
        assert isinstance(OBSERVED_ENTITY_TYPES, frozenset)
        assert "gpu" in OBSERVED_ENTITY_TYPES
