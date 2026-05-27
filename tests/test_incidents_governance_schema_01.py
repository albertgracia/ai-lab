"""Tests for INCIDENTS-GOVERNANCE-SCHEMA-01.

Covers:
1. incidente minimo recibe schema_version
2. incidente minimo recibe incident_id
3. resolved default false
4. archived default false
5. resolution_status default open
6. retention_class por event_type
7. duplicate_count default 0
8. first_seen_at/last_seen_at se asignan
9. dedup_key se conserva si existe
10. critical obtiene retention_class critical_keep
11. service_down no queda archived/resolved
12. payload antiguo compatible
13. no prompt completo
14. no response completa
15. schema builder fail-safe
"""


def test_schema_version_default():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog")
    assert inc["schema_version"] == "INCIDENTS-GOVERNANCE-SCHEMA-01"


def test_incident_id_present():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog")
    assert inc["incident_id"].startswith("WD-")
    assert len(inc["incident_id"]) > 5


def test_resolved_default_false():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="warning",
                          message="test", source="watchdog")
    assert inc["resolved"] is False


def test_resolved_explicit():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_recovered", severity="info",
                          message="test", source="watchdog", resolved=True)
    assert inc["resolved"] is True


def test_archived_default_false():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog")
    assert inc["archived"] is False


def test_resolution_status_default_open():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="warning",
                          message="test", source="watchdog")
    assert inc["resolution_status"] == "open"


def test_resolution_status_resolved_when_resolved():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_recovered", severity="info",
                          message="test", source="watchdog", resolved=True)
    assert inc["resolution_status"] == "resolved"


def test_retention_class_by_event_type():
    from runtime.incidents.incident_schema import build_incident, retention_class_for

    for evt, expected in [("cluster_degraded", "degraded_signal"),
                           ("service_degraded", "degraded_signal"),
                           ("service_down", "down_signal"),
                           ("service_recovered", "recovered_signal"),
                           ("routing_error", "routing_error"),
                           ("unknown_type", "operational_signal")]:
        inc = build_incident(event_type=evt, severity="warning", message="test", source="watchdog")
        assert inc["retention_class"] == expected, f"{evt}: expected {expected}, got {inc['retention_class']}"


def test_critical_retention_class():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="critical",
                          message="test", source="watchdog")
    assert inc["retention_class"] == "critical_keep"


def test_duplicate_count_default():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog")
    assert inc["duplicate_count"] == 0


def test_first_seen_last_seen():
    from runtime.incidents.incident_schema import build_incident
    import time

    now = time.time()
    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog", timestamp=now)
    assert inc["first_seen_at"] == now
    assert inc["last_seen_at"] == now


def test_dedup_key_preserved():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog", dedup_key="test-key-123")
    assert inc.get("dedup_key") == "test-key-123"


def test_dedup_key_absent():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="warning",
                          message="test", source="watchdog")
    assert "dedup_key" not in inc


def test_affected_component_from_service():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="warning",
                          message="test", source="watchdog", service="gateway")
    assert inc["affected_component"] == "gateway"


def test_affected_component_from_node():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="node_failure", severity="critical",
                          message="test", source="watchdog", node="rx9070")
    assert inc["affected_component"] == "rx9070"


def test_no_prompt_in_payload():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message="test", source="watchdog")
    keys = list(inc.keys())
    assert "prompt" not in keys
    assert "response" not in keys
    assert "messages" not in keys
    assert "content" not in keys


def test_message_truncated():
    from runtime.incidents.incident_schema import build_incident

    long_msg = "x" * 2000
    inc = build_incident(event_type="cluster_degraded", severity="warning",
                          message=long_msg, source="watchdog")
    assert len(inc["message"]) <= 500


def test_service_down_payload_compat():
    from runtime.incidents.incident_schema import build_incident

    inc = build_incident(event_type="service_down", severity="warning",
                          message="test", source="watchdog", service="router",
                          status="down")
    assert inc["event_type"] == "service_down"
    assert inc.get("service") == "router"
    assert inc.get("status") == "down"
    assert inc["resolved"] is False
    assert inc["retention_class"] == "down_signal"
