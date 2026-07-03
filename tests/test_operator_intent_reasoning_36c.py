<<<<<<< Updated upstream
"""FASE 36C: Operator Intent Reasoning tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.operator_intent import OPERATOR_INTENT_CONTRACT_VERSION
from runtime.operator_intent import OperatorIntentCategory
from runtime.operator_intent import analyze_operator_intent
from runtime.operator_intent import classify_operator_intent


def _intent(text: str, **kwargs) -> dict:
    return analyze_operator_intent(text, **kwargs)


def test_contract_version_is_36c():
    result = _intent("estado runtime")
    assert result["contract_version"] == OPERATOR_INTENT_CONTRACT_VERSION == "36C"


def test_fast_runtime_status_classification():
    result = _intent("estado runtime")
    assert result["category"] == OperatorIntentCategory.FAST_STATUS.value
    assert result["confidence"]["label"] in {"medium", "high"}
    assert "status_query" in result["reason_codes"]


def test_fast_observability_exporters_classification():
    result = _intent("qué exporters están down")
    assert result["category"] == OperatorIntentCategory.FAST_OBSERVABILITY.value
    assert "exporters" in result["matched_terms"]
    assert result["safety"]["can_execute"] is False


def test_diagnostic_failure_classification():
    result = _intent("analiza el fallo de qwen y la root cause")
    assert result["category"] == OperatorIntentCategory.DIAGNOSTIC.value
    assert "diagnostic_terms" in result["reason_codes"]


def test_forensic_incident_classification():
    result = _intent("análisis forense del incidente p1 con timeline")
    assert result["category"] == OperatorIntentCategory.FORENSIC_ANALYSIS.value
    assert result["ambiguity"]["is_mixed"] is False


def test_architecture_risk_classification():
    result = _intent("qué riesgos arquitectónicos tiene ai-lab y su blast radius")
    assert result["category"] == OperatorIntentCategory.ARCHITECTURAL_REASONING.value
    assert "architecture_terms" in result["reason_codes"]


def test_multi_gpu_preparation_classification():
    result = _intent("cómo preparar multi-gpu con scheduler y failover")
    assert result["category"] == OperatorIntentCategory.MULTI_GPU_PREPARATION.value
    assert "multi_gpu_terms" in result["reason_codes"]


def test_remediation_discussion_has_no_execution_authority():
    result = _intent("cómo arreglar el fallo del gateway")
    assert result["category"] == OperatorIntentCategory.REMEDIATION_DISCUSSION.value
    assert result["safety"]["can_execute"] is False
    assert result["safety"]["execution_authority"] == "none"
    assert result["safety"]["remediation_authority"] == "discussion_only"
    assert result["safety"]["requires_human_confirmation"] is True


def test_implementation_request_has_no_mutation_authority():
    result = _intent("implementa un script y reinicia systemctl restart ailab-gateway")
    assert result["category"] in {
        OperatorIntentCategory.IMPLEMENTATION_REQUEST.value,
        OperatorIntentCategory.MIXED_INTENT.value,
    }
    assert result["safety"]["can_execute"] is False
    assert result["safety"]["infrastructure_mutation_authority"] == "none"
    assert "systemctl restart" in result["safety"]["unsafe_action_markers"]
    assert "NO_AUTONOMOUS_EXECUTION" in result["safety"]["guards"]


def test_unknown_input_is_low_confidence():
    result = _intent("cuéntame algo interesante")
    assert result["category"] == OperatorIntentCategory.UNKNOWN.value
    assert result["confidence"]["label"] == "low"
    assert result["confidence"]["degraded"] is False


def test_mixed_intent_detects_cross_group_query():
    result = _intent("estado runtime y plan para preparar multi-gpu")
    assert result["category"] == OperatorIntentCategory.MIXED_INTENT.value
    assert result["ambiguity"]["is_mixed"] is True
    assert len(result["ambiguity"]["candidates"]) >= 2


def test_degraded_authority_is_metadata_not_score_downgrade():
    baseline = _intent("estado runtime")
    degraded = _intent("estado runtime", authority_snapshot={"freshness": {"status": "stale", "confidence": "low"}})
    assert degraded["category"] == baseline["category"]
    assert degraded["confidence"]["score"] == baseline["confidence"]["score"]
    assert degraded["confidence"]["label"] == baseline["confidence"]["label"]
    assert degraded["confidence"]["degraded"] is True
    assert "authority_not_fresh" in degraded["confidence"]["degraded_reasons"]


def test_partial_precision_is_metadata_not_score_downgrade():
    baseline = _intent("qué modelos están operacionales")
    partial = _intent(
        "qué modelos están operacionales",
        precision_report={"precision": {"operational_precision_score": 0.7, "partial_state_total": 2}},
    )
    assert partial["category"] == baseline["category"]
    assert partial["confidence"]["score"] == baseline["confidence"]["score"]
    assert "precision_partial" in partial["confidence"]["degraded_reasons"]


def test_memory_and_gitnexus_are_readonly_and_do_not_override_authority():
    result = _intent(
        "analiza la arquitectura",
        memory_context={"claim": "override model truth"},
        gitnexus_context={"symbols": ["fake"]},
    )
    assert result["explainability"]["memory_context_readonly"] is True
    assert result["explainability"]["gitnexus_context_readonly"] is True
    assert result["explainability"]["memory_overrides_authority"] is False
    assert "NO_INFERRED_OPERATIONAL_TRUTH" in result["safety"]["guards"]


def test_signature_is_deterministic_for_same_input(monkeypatch):
    monkeypatch.setenv("STRICT_VALIDATION_MODE", "true")
    first = _intent("estado runtime")
    second = _intent("  estado   runtime  ")
    assert first["generated_at"] == second["generated_at"] == 0.0
    assert first["deterministic_signature"] == second["deterministic_signature"]


def test_classify_operator_intent_returns_category_string():
    assert classify_operator_intent("estado GPU RX9070") == OperatorIntentCategory.FAST_GPU_STATUS.value


# ── Extended schema tests (FASE Operator Intent 01) ────────────────


def test_trivia_not_operator():
    result = _intent("What is 2+2?")
    assert result["category"] == OperatorIntentCategory.UNKNOWN.value
    assert result["risk"] == "low"
    assert result["requires_approval"] is False
    assert result["recommended_action"] == "answer"


def test_restart_gateway_is_high_risk_requires_approval():
    result = _intent("restart the gateway")
    assert result["target"] == "gateway"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "require_approval"
    assert result["allowed_modes"] == ["observe"]


def test_show_health_is_low_risk():
    result = _intent("show me AI-LAB health")
    assert result["category"] in {
        OperatorIntentCategory.FAST_STATUS.value,
        OperatorIntentCategory.FAST_OBSERVABILITY.value,
    }
    assert result["risk"] == "low"
    assert result["requires_approval"] is False
    assert result["recommended_action"] == "answer"


def test_delete_logs_is_critical():
    result = _intent("delete all logs")
    assert result["safety"]["unsafe_action_markers"]
    assert result["risk"] == "critical"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "block"
    assert result["allowed_modes"] == ["observe"]


def test_push_to_origin_main_is_high_risk():
    result = _intent("push to origin main")
    assert result["target"] == "git"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "require_approval"


def test_prepare_rollback_plan_is_planning():
    result = _intent("prepare a rollback plan for the gateway")
    assert result["category"] == OperatorIntentCategory.PLANNING.value
    assert result["risk"] == "medium"
    assert result["allowed_modes"] == ["observe", "plan", "build"]
    assert result["recommended_action"] in ("ask_clarification", "require_approval")


def test_rm_rf_is_critical_blocked():
    result = _intent("rm -rf /opt/ai-lab/logs")
    assert result["risk"] == "critical"
    assert result["recommended_action"] == "block"
    assert "unsafe_action_markers" in result["safety"]
    assert result["safety"]["requires_human_confirmation"] is True


def test_deploy_change_is_high_risk():
    result = _intent("deploy this change to the gateway")
    assert result["target"] == "gateway"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["allowed_modes"] == ["observe"]


def test_prometheus_target_down_is_observability():
    result = _intent("find why Prometheus target is down")
    assert result["category"] == OperatorIntentCategory.FAST_OBSERVABILITY.value
    assert result["target"] == "prometheus"
    assert result["risk"] == "low"
=======
"""FASE 36C: Operator Intent Reasoning tests."""

from __future__ import annotations

import sys

sys.path.insert(0, "/opt/ai-lab")

from runtime.operator_intent import OPERATOR_INTENT_CONTRACT_VERSION
from runtime.operator_intent import OperatorIntentCategory
from runtime.operator_intent import analyze_operator_intent
from runtime.operator_intent import classify_operator_intent


def _intent(text: str, **kwargs) -> dict:
    return analyze_operator_intent(text, **kwargs)


def test_contract_version_is_36c():
    result = _intent("estado runtime")
    assert result["contract_version"] == OPERATOR_INTENT_CONTRACT_VERSION == "36C"


def test_fast_runtime_status_classification():
    result = _intent("estado runtime")
    assert result["category"] == OperatorIntentCategory.FAST_STATUS.value
    assert result["confidence"]["label"] in {"medium", "high"}
    assert "status_query" in result["reason_codes"]


def test_fast_observability_exporters_classification():
    result = _intent("qué exporters están down")
    assert result["category"] == OperatorIntentCategory.FAST_OBSERVABILITY.value
    assert "exporters" in result["matched_terms"]
    assert result["safety"]["can_execute"] is False


def test_diagnostic_failure_classification():
    result = _intent("analiza el fallo de qwen y la root cause")
    assert result["category"] == OperatorIntentCategory.DIAGNOSTIC.value
    assert "diagnostic_terms" in result["reason_codes"]


def test_forensic_incident_classification():
    result = _intent("análisis forense del incidente p1 con timeline")
    assert result["category"] == OperatorIntentCategory.FORENSIC_ANALYSIS.value
    assert result["ambiguity"]["is_mixed"] is False


def test_architecture_risk_classification():
    result = _intent("qué riesgos arquitectónicos tiene ai-lab y su blast radius")
    assert result["category"] == OperatorIntentCategory.ARCHITECTURAL_REASONING.value
    assert "architecture_terms" in result["reason_codes"]


def test_multi_gpu_preparation_classification():
    result = _intent("cómo preparar multi-gpu con scheduler y failover")
    assert result["category"] == OperatorIntentCategory.MULTI_GPU_PREPARATION.value
    assert "multi_gpu_terms" in result["reason_codes"]


def test_remediation_discussion_has_no_execution_authority():
    result = _intent("cómo arreglar el fallo del gateway")
    assert result["category"] == OperatorIntentCategory.REMEDIATION_DISCUSSION.value
    assert result["safety"]["can_execute"] is False
    assert result["safety"]["execution_authority"] == "none"
    assert result["safety"]["remediation_authority"] == "discussion_only"
    assert result["safety"]["requires_human_confirmation"] is True


def test_implementation_request_has_no_mutation_authority():
    result = _intent("implementa un script y reinicia systemctl restart ailab-gateway")
    assert result["category"] in {
        OperatorIntentCategory.IMPLEMENTATION_REQUEST.value,
        OperatorIntentCategory.MIXED_INTENT.value,
    }
    assert result["safety"]["can_execute"] is False
    assert result["safety"]["infrastructure_mutation_authority"] == "none"
    assert "systemctl restart" in result["safety"]["unsafe_action_markers"]
    assert "NO_AUTONOMOUS_EXECUTION" in result["safety"]["guards"]


def test_unknown_input_is_low_confidence():
    result = _intent("cuéntame algo interesante")
    assert result["category"] == OperatorIntentCategory.UNKNOWN.value
    assert result["confidence"]["label"] == "low"
    assert result["confidence"]["degraded"] is False


def test_mixed_intent_detects_cross_group_query():
    result = _intent("estado runtime y plan para preparar multi-gpu")
    assert result["category"] == OperatorIntentCategory.MIXED_INTENT.value
    assert result["ambiguity"]["is_mixed"] is True
    assert len(result["ambiguity"]["candidates"]) >= 2


def test_degraded_authority_is_metadata_not_score_downgrade():
    baseline = _intent("estado runtime")
    degraded = _intent("estado runtime", authority_snapshot={"freshness": {"status": "stale", "confidence": "low"}})
    assert degraded["category"] == baseline["category"]
    assert degraded["confidence"]["score"] == baseline["confidence"]["score"]
    assert degraded["confidence"]["label"] == baseline["confidence"]["label"]
    assert degraded["confidence"]["degraded"] is True
    assert "authority_not_fresh" in degraded["confidence"]["degraded_reasons"]


def test_partial_precision_is_metadata_not_score_downgrade():
    baseline = _intent("qué modelos están operacionales")
    partial = _intent(
        "qué modelos están operacionales",
        precision_report={"precision": {"operational_precision_score": 0.7, "partial_state_total": 2}},
    )
    assert partial["category"] == baseline["category"]
    assert partial["confidence"]["score"] == baseline["confidence"]["score"]
    assert "precision_partial" in partial["confidence"]["degraded_reasons"]


def test_memory_and_gitnexus_are_readonly_and_do_not_override_authority():
    result = _intent(
        "analiza la arquitectura",
        memory_context={"claim": "override model truth"},
        gitnexus_context={"symbols": ["fake"]},
    )
    assert result["explainability"]["memory_context_readonly"] is True
    assert result["explainability"]["gitnexus_context_readonly"] is True
    assert result["explainability"]["memory_overrides_authority"] is False
    assert "NO_INFERRED_OPERATIONAL_TRUTH" in result["safety"]["guards"]


def test_signature_is_deterministic_for_same_input(monkeypatch):
    monkeypatch.setenv("STRICT_VALIDATION_MODE", "true")
    first = _intent("estado runtime")
    second = _intent("  estado   runtime  ")
    assert first["generated_at"] == second["generated_at"] == 0.0
    assert first["deterministic_signature"] == second["deterministic_signature"]


def test_classify_operator_intent_returns_category_string():
    assert classify_operator_intent("estado GPU RX9070") == OperatorIntentCategory.FAST_GPU_STATUS.value


# ── Extended schema tests (FASE Operator Intent 01) ────────────────


def test_trivia_not_operator():
    result = _intent("What is 2+2?")
    assert result["category"] == OperatorIntentCategory.UNKNOWN.value
    assert result["risk"] == "low"
    assert result["requires_approval"] is False
    assert result["recommended_action"] == "answer"


def test_restart_gateway_is_high_risk_requires_approval():
    result = _intent("restart the gateway")
    assert result["target"] == "gateway"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "require_approval"
    assert result["allowed_modes"] == ["observe"]


def test_show_health_is_low_risk():
    result = _intent("show me AI-LAB health")
    assert result["category"] in {
        OperatorIntentCategory.FAST_STATUS.value,
        OperatorIntentCategory.FAST_OBSERVABILITY.value,
    }
    assert result["risk"] == "low"
    assert result["requires_approval"] is False
    assert result["recommended_action"] == "answer"


def test_delete_logs_is_critical():
    result = _intent("delete all logs")
    assert result["safety"]["unsafe_action_markers"]
    assert result["risk"] == "critical"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "block"
    assert result["allowed_modes"] == ["observe"]


def test_push_to_origin_main_is_high_risk():
    result = _intent("push to origin main")
    assert result["target"] == "git"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["recommended_action"] == "require_approval"


def test_prepare_rollback_plan_is_planning():
    result = _intent("prepare a rollback plan for the gateway")
    assert result["category"] == OperatorIntentCategory.PLANNING.value
    assert result["risk"] == "medium"
    assert result["allowed_modes"] == ["observe", "plan", "build"]
    assert result["recommended_action"] in ("ask_clarification", "require_approval")


def test_rm_rf_is_critical_blocked():
    result = _intent("rm -rf /opt/ai-lab/logs")
    assert result["risk"] == "critical"
    assert result["recommended_action"] == "block"
    assert "unsafe_action_markers" in result["safety"]
    assert result["safety"]["requires_human_confirmation"] is True


def test_deploy_change_is_high_risk():
    result = _intent("deploy this change to the gateway")
    assert result["target"] == "gateway"
    assert result["risk"] == "high"
    assert result["requires_approval"] is True
    assert result["allowed_modes"] == ["observe"]


def test_prometheus_target_down_is_observability():
    result = _intent("find why Prometheus target is down")
    assert result["category"] == OperatorIntentCategory.FAST_OBSERVABILITY.value
    assert result["target"] == "prometheus"
    assert result["risk"] == "low"
>>>>>>> Stashed changes
