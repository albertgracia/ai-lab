"""FASE 30H.1: Universal Evidence Guard tests.

Tests that evidence guard applies to ALL routes when runtime-state intent is detected,
not just report/minimal routes.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from runtime.context.evidence_guard import (
    ReportEvidenceResult,
    sanitize_unverified_claims,
    build_evidence_catalog,
)
from runtime.gateway.tool_request_classifier import (
    detect_runtime_grounded_intent,
    should_apply_evidence_guard,
    sanitize_report_output,
)


# ── Test evidence catalog ──────────────────────────────────

_BASE_RUNTIME_CONTEXT: dict[str, Any] = {
    "runtime_hostname": "ubuntu-ialab",
    "primary_runtime_ip": "192.168.1.30",
    "inference_nodes": {
        "active": [
            {"name": "RX9070", "host": "192.168.1.50"},
        ],
        "inventory": [
            {"name": "RX7900XT", "host": "192.168.1.60"},
        ],
    },
    "models": {
        "active": [
            {"id": "llama-3.1-8b-instruct"},
            {"id": "qwen2.5-coder-14b-instruct"},
        ],
        "disabled": [
            {"id": "qwen/qwen3.6-27b"},
        ],
        "discovered": [
            {"id": "lmstudio-community/qwen2.5-coder-14b-instruct"},
        ],
    },
    "services": {
        "core": ["ailab-gateway (:8008)"],
        "observability": [
            {"name": "prometheus", "url": "http://192.168.1.40:9090"},
        ],
    },
    "profiles_available": ["minimal", "report", "coding", "chat"],
}


class TestShouldApplyEvidenceGuard(unittest.TestCase):
    """Tests for should_apply_evidence_guard detection logic."""

    def test_evidence_guard_applies_to_cognitive_runtime_question(self):
        """Cognitive route with runtime question must apply evidence guard."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "cognitive",
            "Describe cómo está funcionando AI-LAB actualmente",
        )
        self.assertIsNotNone(scope)
        self.assertEqual(scope, "runtime_intent")

    def test_evidence_guard_applies_when_report_grounded_true(self):
        """Payload with _report_grounded=True must apply evidence guard."""
        payload: dict[str, Any] = {"_report_grounded": True}
        scope = should_apply_evidence_guard(
            payload, "cognitive",
            "Háblame de cualquier cosa",
        )
        self.assertIsNotNone(scope)
        self.assertEqual(scope, "grounded_runtime")

    def test_evidence_guard_applies_when_runtime_context_exists(self):
        """Payload with _report_runtime_context must apply evidence guard."""
        payload: dict[str, Any] = {"_report_runtime_context": json.dumps({})}
        scope = should_apply_evidence_guard(
            payload, "cognitive",
            "Háblame de cualquier cosa",
        )
        self.assertIsNotNone(scope)
        self.assertEqual(scope, "grounded_runtime")

    def test_evidence_guard_skips_general_non_runtime_chat(self):
        """Cognitive non-runtime chat should NOT apply evidence guard."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "cognitive",
            "¿Cuál es la capital de Francia?",
        )
        self.assertIsNone(scope)

    def test_guard_scope_grounded_runtime(self):
        """Report route with _report_grounded should get grounded_runtime scope."""
        payload: dict[str, Any] = {"_report_grounded": True}
        scope = should_apply_evidence_guard(
            payload, "report",
            "Dame un informe del estado",
        )
        self.assertEqual(scope, "grounded_runtime")

    def test_guard_scope_runtime_intent(self):
        """Analysis route with GPU mention should get runtime_intent scope."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "analysis",
            "¿Cómo está funcionando la GPU RX9070 en AI-LAB?",
        )
        self.assertEqual(scope, "runtime_intent")

    def test_non_runtime_cognitive_not_guarded(self):
        """Pure creative/cognitive with no runtime keywords should not be guarded."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "cognitive",
            "Escribe un poema sobre la luna",
        )
        self.assertIsNone(scope)

    def test_observe_route_gpu_question_guarded(self):
        """Observe route asking about GPU should be guarded."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "observe",
            "¿Qué GPU tiene el laboratorio?",
        )
        self.assertEqual(scope, "runtime_intent")

    def test_learning_route_evidence_guarded(self):
        """Learning route with prometheus mention should be guarded."""
        payload: dict[str, Any] = {}
        scope = should_apply_evidence_guard(
            payload, "learning",
            "¿Cómo se configuró Prometheus en AI-LAB?",
        )
        self.assertEqual(scope, "runtime_intent")


class TestEvidenceGuardScope(unittest.TestCase):
    """Tests for evidence guard scope in ReportEvidenceResult."""

    def test_default_scope_is_fallback_disabled(self):
        """Default scope should be fallback_disabled when no scope provided."""
        result = sanitize_unverified_claims(
            "Everything is fine.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
        )
        self.assertEqual(result.guard_scope, "fallback_disabled")

    def test_scope_is_set_correctly(self):
        """Scope should be set to the provided value."""
        result = sanitize_unverified_claims(
            "The server runs on AWS EC2 with NVIDIA A100.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
            model="qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            guard_scope="runtime_intent",
        )
        self.assertEqual(result.guard_scope, "runtime_intent")

    def test_model_and_route_family_propagated(self):
        """Model and route_family should propagate to result."""
        result = sanitize_unverified_claims(
            "Testing",
            runtime_context=_BASE_RUNTIME_CONTEXT,
            model="llama-3.1-8b-instruct",
            route_family="cognitive",
            guard_scope="runtime_intent",
        )
        self.assertEqual(result.model, "llama-3.1-8b-instruct")
        self.assertEqual(result.route_family, "cognitive")
        self.assertEqual(result.guard_scope, "runtime_intent")

    def test_scoped_guard_catches_gpu_hallucination(self):
        """Evidence guard with scope should catch hallucinated GPUs."""
        result = sanitize_unverified_claims(
            "The system runs on NVIDIA A100 GPUS.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
            model="qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            guard_scope="runtime_intent",
        )
        self.assertGreater(len(result.unverified_claims), 0)
        self.assertTrue(
            any("a100" in c.lower() for c in result.unverified_claims)
        )

    def test_evidence_guard_applies_to_cognitive_with_false_gpus(self):
        """Cognitive route generating false GPU info should be caught by evidence guard."""
        from runtime.context.evidence_guard import sanitize_unverified_claims

        result = sanitize_unverified_claims(
            "AI-LAB utiliza NVIDIA A100 y H100 para inferencia con GPT-4.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
            model="qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            guard_scope="runtime_intent",
        )
        self.assertGreater(len(result.unverified_claims), 0)
        gpu_claims = [c for c in result.unverified_claims if "a100" in c.lower() or "h100" in c.lower()]
        self.assertGreater(len(gpu_claims), 0)
        self.assertIn("[EVIDENCE GUARD]", result.sanitized_text)

    def test_qwen_runtime_prompt_is_guarded(self):
        """qwen answering runtime question about GPT-4 should be detected."""
        scope = should_apply_evidence_guard(
            {}, "cognitive",
            "Describe cómo está funcionando GPT4-8K dentro de AI-LAB",
        )
        # GPT4 isn't in the triggers, but "ai-lab" is
        self.assertEqual(scope, "runtime_intent")

    def test_llama_runtime_prompt_is_guarded(self):
        """llama answering runtime question should be guarded."""
        scope = should_apply_evidence_guard(
            {}, "minimal",
            "¿Qué modelos tiene AI-LAB cargados?",
        )
        self.assertIsNotNone(scope)

    def test_evidence_guard_blocks_external_platform_claim(self):
        """Evidence guard should flag AWS/GCP/Azure as external platforms."""
        from runtime.context.evidence_guard import sanitize_unverified_claims

        result = sanitize_unverified_claims(
            "AWS y Google Cloud coordinan AI-LAB.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
            model="qwen2.5-coder-14b-instruct",
            route_family="cognitive",
            guard_scope="runtime_intent",
        )
        self.assertGreater(len(result.unverified_claims), 0)
        self.assertIn("[EVIDENCE GUARD]", result.sanitized_text)


class TestSanitizeReportOutputUniversal(unittest.TestCase):
    """Tests for sanitize_report_output with universal evidence guard."""

    def test_sanitize_report_output_with_context(self):
        """sanitize_report_output should apply evidence guard with context."""
        content = "El cluster usa NVIDIA A100 y AWS."
        cleaned, found = sanitize_report_output(
            content,
            runtime_context_json=json.dumps(_BASE_RUNTIME_CONTEXT),
        )
        self.assertGreater(len(found), 0)
        self.assertIn("[EVIDENCE GUARD]", cleaned)

    def test_sanitize_report_output_clean(self):
        """sanitize_report_output with no violations should be unchanged."""
        content = "AI-LAB usa RX9070 con qwen2.5-coder-14b."
        cleaned, found = sanitize_report_output(
            content,
            runtime_context_json=json.dumps(_BASE_RUNTIME_CONTEXT),
        )
        self.assertEqual(len(found), 0)
        self.assertEqual(cleaned, content)

    def test_sanitize_report_output_universal_guard(self):
        """sanitize_report_output should guard against GPT-4 mention."""
        content = "GPT-4 está desplegado en AI-LAB."
        cleaned, found = sanitize_report_output(
            content,
            runtime_context_json=json.dumps(_BASE_RUNTIME_CONTEXT),
        )
        self.assertGreater(len(found), 0)
        gpt_found = any("gpt-4" in c.lower() for c in found)
        self.assertTrue(gpt_found)


class TestDetectRuntimeGroundedIntent(unittest.TestCase):
    """Tests for the standalone detect_runtime_grounded_intent function."""

    def test_detect_ai_lab(self):
        """'ai-lab' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Cómo está AI-LAB?"))

    def test_detect_gpu(self):
        """'gpu' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Qué GPU usa el laboratorio?"))

    def test_detect_scheduler(self):
        """'scheduler' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Cómo funciona el scheduler?"))

    def test_detect_kubernetes(self):
        """'kubernetes' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Kubernetes coordina AI-LAB?"))

    def test_detect_prometheus(self):
        """'prometheus' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Cómo se configuró Prometheus?"))

    def test_detect_observability(self):
        """'observabilidad' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Qué observabilidad tiene AI-LAB?"))

    def test_detect_slo(self):
        """'slo' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Cómo está el SLO del runtime?"))

    def test_non_runtime_text_not_detected(self):
        """Generic text without runtime keywords should not be detected."""
        self.assertFalse(detect_runtime_grounded_intent("¿Cuál es la capital de Francia?"))
        self.assertFalse(detect_runtime_grounded_intent("Escribe un poema"))
        self.assertFalse(detect_runtime_grounded_intent("Hola, ¿cómo estás?"))

    def test_observed_runtime_in_system_prompt(self):
        """OBSERVED_RUNTIME in system_prompt should be detected."""
        self.assertTrue(detect_runtime_grounded_intent(
            "Dime algo", system_prompt="OBSERVED_RUNTIME: {...}"
        ))

    def test_detect_telemetry(self):
        """'telemetry' in text should be detected as runtime intent."""
        self.assertTrue(detect_runtime_grounded_intent("¿Cómo funciona la telemetría?"))


class TestEvidenceGuardRuntimeIntentDetected(unittest.TestCase):
    """Tests for runtime_intent_detected field in ReportEvidenceResult."""

    def test_runtime_intent_detected_default_false(self):
        """Default runtime_intent_detected should be False."""
        result = sanitize_unverified_claims(
            "Everything is fine.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
        )
        self.assertFalse(result.runtime_intent_detected)

    def test_runtime_intent_detected_set_true(self):
        """runtime_intent_detected can be set to True."""
        result = sanitize_unverified_claims(
            "AI-LAB está funcionando.",
            runtime_context=_BASE_RUNTIME_CONTEXT,
        )
        # The field exists and can be modified
        result.runtime_intent_detected = True
        self.assertTrue(result.runtime_intent_detected)


class TestMultiModelEvidenceGuard(unittest.TestCase):
    """Tests that evidence guard works for both llama and qwen models."""

    def test_llama_runtime_prompt_guarded(self):
        """llama model on runtime question should be guarded (minimal route=report_route)."""
        scope = should_apply_evidence_guard(
            {}, "minimal",
            "¿Cómo está funcionando el gateway de AI-LAB?",
        )
        # Minimal route gets report_route scope because route_family is checked first
        self.assertIsNotNone(scope)

    def test_qwen_runtime_prompt_guarded(self):
        """qwen model on runtime question should be guarded."""
        scope = should_apply_evidence_guard(
            {}, "cognitive",
            "Descríbeme la topología del runtime AI-LAB",
        )
        self.assertEqual(scope, "runtime_intent")

    def test_qwen_gpu_question_guarded(self):
        """qwen answering GPU question should be guarded."""
        scope = should_apply_evidence_guard(
            {}, "cognitive",
            "¿Qué GPUs tiene AI-LAB disponibles?",
        )
        self.assertEqual(scope, "runtime_intent")

    def test_llama_non_runtime_not_guarded(self):
        """llama on non-runtime chat should not be guarded (uses observe route to avoid route-based guard)."""
        scope = should_apply_evidence_guard(
            {}, "observe",
            "¿Cuál es la receta de la paella?",
        )
        self.assertIsNone(scope)

    def test_qwen_non_runtime_not_guarded(self):
        """qwen on non-runtime chat should not be guarded."""
        scope = should_apply_evidence_guard(
            {}, "cognitive",
            "Explica la teoría de la relatividad",
        )
        self.assertIsNone(scope)


class TestScopedMetricsRegistration(unittest.TestCase):
    """Tests that scoped metrics are properly registered."""

    def test_scoped_metric_exists(self):
        """ailab_report_evidence_guard_scoped_total metric should be registered."""
        from runtime.telemetry.prometheus_metrics import REPORT_EVIDENCE_GUARD_SCOPED_TOTAL
        self.assertIsNotNone(REPORT_EVIDENCE_GUARD_SCOPED_TOTAL)
        # Prometheus Counter._name stores base name without _total suffix
        self.assertIn(
            "ailab_report_evidence_guard_scoped",
            REPORT_EVIDENCE_GUARD_SCOPED_TOTAL._name,
        )

    def test_autoinjected_metric_exists(self):
        """ailab_runtime_context_autoinjected_total metric should be registered."""
        from runtime.telemetry.prometheus_metrics import RUNTIME_CONTEXT_AUTOINJECTED_TOTAL
        self.assertIsNotNone(RUNTIME_CONTEXT_AUTOINJECTED_TOTAL)
        # Prometheus Counter._name stores base name without _total suffix
        self.assertIn(
            "ailab_runtime_context_autoinjected",
            RUNTIME_CONTEXT_AUTOINJECTED_TOTAL._name,
        )

    def test_record_runtime_context_autoinjected(self):
        """record_runtime_context_autoinjected should not raise."""
        from runtime.telemetry.prometheus_metrics import record_runtime_context_autoinjected
        record_runtime_context_autoinjected()


if __name__ == "__main__":
    unittest.main()
