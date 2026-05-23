from __future__ import annotations

import os
import sys

sys.path.insert(0, "/opt/ai-lab")


def _discovery(*, timestamp=1000, ttl=60, online=True, error=None, models=None):
    return {
        "timestamp": timestamp,
        "ttl_seconds": ttl,
        "nodes": [
            {
                "name": "rx9070-node",
                "host": "192.168.1.50",
                "port": 1234,
                "online": online,
                "latency_ms": 12.0,
                "error": error,
                "models": models if models is not None else [{"id": "qwen/qwen2.5-coder-14b-instruct"}],
            }
        ],
        "models_found": len(models if models is not None else [1]),
        "online_nodes": 1 if online else 0,
        "total_nodes": 1,
    }


def test_discoverable_is_not_operational_when_ctx_zero(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 1000)
    monkeypatch.setattr("runtime.models.operational_truth._metadata", lambda model_id: {"id": model_id, "skills": ["coding"], "context_window": 0, "source": "test"})
    truth = build_operational_model_truth(discovery=_discovery())
    assert truth["summary"]["operational_total"] == 0
    assert truth["summary"]["ctx_zero_rejected"] == 1
    assert truth["discoverable_only_models"][0]["operational"] is False


def test_empty_skills_rejected(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 1000)
    monkeypatch.setattr("runtime.models.operational_truth._metadata", lambda model_id: {"id": model_id, "skills": [], "context_window": 32768, "source": "test"})
    truth = build_operational_model_truth(discovery=_discovery())
    assert truth["summary"]["operational_total"] == 0
    assert truth["summary"]["empty_skills_rejected"] == 1


def test_stale_authority_downgrades_operational(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 2000)
    truth = build_operational_model_truth(discovery=_discovery(timestamp=1000, ttl=60))
    assert truth["freshness"]["status"] == "expired"
    assert truth["summary"]["operational_total"] == 0
    assert "stale_model_authority" in truth["confidence"]["reasons"]


def test_unhealthy_backend_rejected(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 1000)
    truth = build_operational_model_truth(discovery=_discovery(online=False, error="connection refused"))
    assert truth["summary"]["operational_total"] == 0
    assert truth["summary"]["unhealthy_rejected"] == 1


def test_operation_canceled_handling(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 1000)
    truth = build_operational_model_truth(discovery=_discovery(online=False, error='Failed to load model "x". Error: Operation canceled'))
    assert truth["summary"]["operational_total"] == 0
    assert "operation_canceled" in truth["confidence"]["reasons"]
    assert "operation_canceled" in truth["rejected_models"][0]["rejection_reasons"]


def test_valid_model_is_operational(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    monkeypatch.setattr("runtime.models.operational_truth._now", lambda: 1000)
    truth = build_operational_model_truth(discovery=_discovery())
    assert truth["summary"]["operational_total"] == 1
    model = truth["operational_models"][0]
    assert model["ctx"] > 0
    assert model["skills"]
    assert model["operational"] is True


def test_deterministic_operational_truth(monkeypatch):
    from runtime.models.operational_truth import build_operational_model_truth

    os.environ["STRICT_VALIDATION_MODE"] = "true"
    try:
        d = _discovery(timestamp=0)
        r1 = build_operational_model_truth(discovery=d)
        r2 = build_operational_model_truth(discovery=d)
        assert r1["deterministic_signature"] == r2["deterministic_signature"]
    finally:
        os.environ.pop("STRICT_VALIDATION_MODE", None)


def test_precision_marks_discoverable_only_partial(monkeypatch):
    from runtime.precision.runtime_precision_mode import build_runtime_precision_report

    model_truth = build_operational_model_truth_for_test = {
        "freshness": {"status": "fresh", "confidence": "high", "reasons": []},
        "summary": {"operational_total": 0, "loaded_total": 1, "discoverable_only_total": 1, "rejected_total": 1, "ctx_zero_rejected": 1, "empty_skills_rejected": 0},
        "operational_models": [],
        "discoverable_only_models": [{"id": "bad", "ctx": 0, "skills": [], "operational": False}],
        "confidence": {"score": 45, "label": "low", "reasons": ["no_operational_models"]},
    }
    authority = {
        "contract_version": "35C",
        "prometheus": {"targets": {"scrape_up": 1, "active_total": 1}},
        "freshness": {"status": "fresh", "confidence": "high", "reasons": []},
        "gaps": [],
        "operational_truth": {"operational_nodes": [], "models": model_truth},
    }
    monkeypatch.setattr("runtime.authority.build_live_authority_snapshot", lambda **kwargs: authority)
    monkeypatch.setattr("runtime.entities.entity_registry.build_routability_summary", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_discoverable_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.entities.entity_registry.build_inventory_entities", lambda *a, **k: [])
    monkeypatch.setattr("runtime.incidents.incident_summary.build_incident_intelligence_summary", lambda **k: {})
    monkeypatch.setattr("runtime.codebase.gitnexus_memory.build_codebase_summary", lambda **k: {})
    rep = build_runtime_precision_report(extra_ctx={"enable_network": False}, sensor_snapshot={})
    assert rep["models"]["ctx_zero_rejected"] == 1
    assert any(p.get("domain") == "models" for p in rep.get("partial", []))
