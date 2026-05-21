"""FASE 30H: Runtime Evidence Enforcement — epistemological discipline."""

import json
import pytest
from pathlib import Path

from runtime.context.evidence_guard import (
    STRICT_EVIDENCE_MODE,
    MAX_UNVERIFIED_CLAIMS,
    build_evidence_catalog,
    sanitize_unverified_claims,
    ReportEvidenceResult,
)
from runtime.gateway.tool_request_classifier import (
    sanitize_report_output,
)
from runtime.maturity.descriptor import RuntimePhase
from runtime.maturity.builder import _resolve_generation_phase
from runtime.telemetry.prometheus_metrics import (
    record_report_evidence_guard,
    record_report_unverified_claim,
    record_report_evidence_score,
    record_report_hallucination_suppressed,
    REPORT_EVIDENCE_GUARD_TOTAL,
    REPORT_UNVERIFIED_CLAIM_TOTAL,
    REPORT_EVIDENCE_SCORE,
    REPORT_HALLUCINATION_SUPPRESSED_TOTAL,
)


# ── Helpers ─────────────────────────────────────────────────────

SAMPLE_RUNTIME_CONTEXT = {
    "runtime_hostname": "ubuntu-ialab",
    "primary_runtime_ip": "192.168.1.30",
    "models": {
        "active": [
            {"id": "llama-3.1-8b-instruct", "role": "lightweight"},
            {"id": "qwen2.5-coder-14b-instruct", "role": "coding"},
            {"id": "text-embedding-nomic-embed-text-v1.5", "role": "embeddings"},
        ],
        "disabled": [
            {"id": "qwen/qwen3.6-27b", "disabled_reason": "removed FASE 29.3"},
        ],
        "discovered": [
            {"id": "lmstudio-community/qwen2.5-coder-14b-instruct", "note": "alias"},
        ],
    },
    "inference_nodes": {
        "active": [
            {"name": "RX9070", "role": "primary inference", "host": "192.168.1.50"},
        ],
        "inventory": [
            {"name": "RX7900XT", "role": "future backend", "host": "192.168.1.60"},
        ],
    },
    "services": {
        "core": ["ailab-gateway (:8008)", "ailab-router (:8083)", "ailab-live-api (:8084)"],
        "support": ["ailab-docs (:4322)", "ailab-heartbeat", "ailab-metrics (:3010)", "ailab-runner"],
        "observability": [
            {"name": "prometheus", "url": "http://192.168.1.40:9090"},
            {"name": "grafana", "url": "http://192.168.1.40:3000"},
        ],
    },
    "profiles_available": ["minimal", "report", "coding", "chat", "analysis", "creative", "agent", "observe"],
}

RUNTIME_CTX_JSON = json.dumps(SAMPLE_RUNTIME_CONTEXT)


# ── build_evidence_catalog ─────────────────────────────────────

def test_build_evidence_catalog_none():
    catalog = build_evidence_catalog(None)
    assert isinstance(catalog, dict)
    assert catalog["models"] == set()
    assert catalog["nodes"] == set()
    assert catalog["hosts"] == set()


def test_build_evidence_catalog_models():
    catalog = build_evidence_catalog(SAMPLE_RUNTIME_CONTEXT)
    assert "llama-3.1-8b-instruct" in catalog["models"]
    assert "qwen2.5-coder-14b-instruct" in catalog["models"]
    assert "text-embedding-nomic-embed-text-v1.5" in catalog["models"]
    assert "qwen/qwen3.6-27b" in catalog["models"]


def test_build_evidence_catalog_model_aliases():
    catalog = build_evidence_catalog(SAMPLE_RUNTIME_CONTEXT)
    assert "qwen2.5-coder-14b-instruct" in catalog["models"]


def test_build_evidence_catalog_nodes():
    catalog = build_evidence_catalog(SAMPLE_RUNTIME_CONTEXT)
    assert "rx9070" in catalog["nodes"]
    assert "rx7900xt" in catalog["nodes"]
    assert "192.168.1.50" in catalog["hosts"]
    assert "192.168.1.60" in catalog["hosts"]


def test_build_evidence_catalog_identity():
    catalog = build_evidence_catalog(SAMPLE_RUNTIME_CONTEXT)
    assert "ubuntu-ialab" in catalog["hosts"]
    assert "192.168.1.30" in catalog["hosts"]


# ── sanitize_unverified_claims: forbidden models ──────────────

def test_detects_forbidden_model_gpt():
    result = sanitize_unverified_claims(
        "Se recomienda usar GPT-4 para tareas complejas.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("model_not_in_observed:GPT-4" in c for c in result.unverified_claims)


def test_detects_forbidden_model_claude():
    result = sanitize_unverified_claims(
        "Claude-3-opus ofrece mejor razonamiento.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("model_not_in_observed" in c for c in result.unverified_claims)


def test_allows_known_model_qwen():
    result = sanitize_unverified_claims(
        "qwen2.5-coder-14b-instruct es el modelo activo.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    qwen_claims = [c for c in result.unverified_claims if "qwen2.5-coder-14b" in c]
    assert qwen_claims == []


def test_allows_known_model_llama():
    result = sanitize_unverified_claims(
        "llama-3.1-8b-instruct maneja tareas ligeras.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    llama_claims = [c for c in result.unverified_claims if "llama-3.1-8b" in c]
    assert llama_claims == []


# ── sanitize_unverified_claims: forbidden GPUs ────────────────

def test_detects_forbidden_gpu_a100():
    result = sanitize_unverified_claims(
        "El cluster cuenta con NVIDIA A100 para inferencia.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("gpu_not_in_observed" in c for c in result.unverified_claims)


def test_detects_forbidden_gpu_h100():
    result = sanitize_unverified_claims(
        "Se necesita H100 para el modelo de 70B.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("gpu_not_in_observed" in c for c in result.unverified_claims)


def test_allows_known_gpu_rx9070():
    result = sanitize_unverified_claims(
        "RX9070 gestiona 3 modelos concurrentes.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    gpu_claims = [c for c in result.unverified_claims if "RX9070" in c]
    assert gpu_claims == []


# ── sanitize_unverified_claims: forbidden security tools ──────

def test_detects_forbidden_security_selinux():
    result = sanitize_unverified_claims(
        "SELinux esta configurado en modo enforcing.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("security_tool_not_in_runtime" in c for c in result.unverified_claims)


def test_detects_forbidden_security_apparmor():
    result = sanitize_unverified_claims(
        "AppArmor protege los contenedores.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("security_tool_not_in_runtime" in c for c in result.unverified_claims)


# ── sanitize_unverified_claims: forbidden external platforms ──

def test_detects_external_platform_aws():
    result = sanitize_unverified_claims(
        "El runtime esta desplegado en AWS EC2.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("external_platform_not_in_runtime" in c for c in result.unverified_claims)


def test_detects_external_platform_gcp():
    result = sanitize_unverified_claims(
        "Se recomienda migrar a Google Cloud.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("external_platform_not_in_runtime" in c for c in result.unverified_claims)


# ── sanitize_unverified_claims: forbidden orchestration tools ──

def test_detects_kubernetes():
    result = sanitize_unverified_claims(
        "Kubernetes coordina los servicios de AI-LAB.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("orchestration_tool_not_in_runtime" in c for c in result.unverified_claims)


def test_detects_spark():
    result = sanitize_unverified_claims(
        "Apache Spark procesa datos en AI-LAB.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("spark" in c.lower() for c in result.unverified_claims)


def test_detects_dask():
    result = sanitize_unverified_claims(
        "Dask se usa para computacion paralela en AI-LAB.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("dask" in c.lower() for c in result.unverified_claims)


def test_detects_ray():
    result = sanitize_unverified_claims(
        "Ray se usa para entrenar modelos en AI-LAB.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("ray" in c.lower() for c in result.unverified_claims)


def test_detects_ubuntu_version():
    result = sanitize_unverified_claims(
        "El servidor corre Ubuntu 23.10.1.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("os_version" in c for c in result.unverified_claims)


def test_detects_centos_version():
    result = sanitize_unverified_claims(
        "El runtime usa CentOS 9 para produccion.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert any("centos" in c.lower() or "os_version" in c for c in result.unverified_claims)


# ── sanitize_unverified_claims: clean content ─────────────────

def test_allows_clean_report():
    result = sanitize_unverified_claims(
        "AI-LAB runtime operativo en 192.168.1.30. "
        "Modelos: qwen2.5-coder-14b-instruct y llama-3.1-8b-instruct. "
        "GPU RX9070 en 192.168.1.50.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert result.unverified_claims == []


def test_empty_content():
    result = sanitize_unverified_claims("", runtime_context=SAMPLE_RUNTIME_CONTEXT)
    assert result.unverified_claims == []
    assert result.evidence_score == 1.0


def test_none_content():
    result = sanitize_unverified_claims(None, runtime_context=SAMPLE_RUNTIME_CONTEXT)
    assert result.unverified_claims == []
    assert result.evidence_score == 1.0


# ── Evidence score & hallucination risk ───────────────────────

def test_evidence_score_perfect():
    result = sanitize_unverified_claims(
        "AI-LAB runtime estable.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert result.evidence_score == 1.0
    assert result.hallucination_risk == "low"


def test_evidence_score_medium_risk():
    result = sanitize_unverified_claims(
        "Usar GPT-4, Claude-3, y H100 para carga pesada. "
        "SELinux activo en AWS.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert result.evidence_score < 0.5
    assert result.hallucination_risk in ("medium", "high")


def test_evidence_score_high_risk():
    many_claims = "GPT-4. " * 10
    result = sanitize_unverified_claims(
        many_claims,
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert result.hallucination_risk == "high"
    assert result.evidence_score <= 0.4


def test_sanitization_appends_note():
    result = sanitize_unverified_claims(
        "Usar GPT-4 para resumenes.",
        runtime_context=SAMPLE_RUNTIME_CONTEXT,
    )
    assert result.sanitized_text != result
    assert "[EVIDENCE GUARD]" in result.sanitized_text
    assert "model_not_in_observed:GPT-4" in result.sanitized_text


# ── Evidence guard integration with sanitize_report_output ────

def test_sanitize_report_output_evidence_guard_integration():
    content = (
        "Reporte: AI-LAB en 192.168.1.30. "
        "Se recomienda usar GPT-4 y NVIDIA A100."
    )
    result, found = sanitize_report_output(content, runtime_context_json=RUNTIME_CTX_JSON)
    assert "model_not_in_observed:GPT-4" in found or any("gpt" in c.lower() for c in found)
    assert "gpu_not_in_observed" in str(found).lower() or any("a100" in c.lower() for c in found)
    assert "[EVIDENCE GUARD]" in result


def test_sanitize_report_output_clean_with_evidence():
    content = (
        "Reporte: AI-LAB con qwen2.5-coder-14b-instruct "
        "en GPU RX9070."
    )
    result, found = sanitize_report_output(content, runtime_context_json=RUNTIME_CTX_JSON)
    evidence_claims = [c for c in found if not c.startswith("datadog") and not "DISCIPLINA" in c]
    assert len(evidence_claims) == 0


# ── RuntimePhase ──────────────────────────────────────────────

def test_runtime_phase_has_30H():
    assert RuntimePhase.PHASE_30H.value == "30H"


def test_resolve_generation_phase_returns_30h():
    phase = _resolve_generation_phase()
    assert phase == "30H"


# ── Metric recorders ──────────────────────────────────────────

def test_record_report_evidence_guard_called():
    record_report_evidence_guard()
    val = REPORT_EVIDENCE_GUARD_TOTAL._value.get()
    assert val >= 1


def test_record_report_unverified_claim_called():
    record_report_unverified_claim(3)
    val = REPORT_UNVERIFIED_CLAIM_TOTAL.labels(count="3")._value.get()
    assert val >= 1


def test_record_report_evidence_score_called():
    record_report_evidence_score(0.85)
    # Histogram — verify no exception


def test_record_report_hallucination_suppressed_called():
    record_report_hallucination_suppressed()
    val = REPORT_HALLUCINATION_SUPPRESSED_TOTAL._value.get()
    assert val >= 1


# ── Configuration ─────────────────────────────────────────────

def test_strict_evidence_mode_default():
    assert STRICT_EVIDENCE_MODE is True


def test_max_unverified_claims_default():
    assert MAX_UNVERIFIED_CLAIMS == 5


# ── ReportEvidenceResult dataclass ────────────────────────────

def test_report_evidence_result_defaults():
    r = ReportEvidenceResult()
    assert r.sanitized_text == ""
    assert r.unverified_claims == []
    assert r.evidence_score == 1.0
    assert r.hallucination_risk == "low"
    assert r.warnings == []
    assert r.suppressed_count == 0
    assert r.strict_mode is True
