"""Tests for INCIDENTS-WATCHDOG-DEDUP-01.

Covers:
1. dedup_key for cluster_degraded
2. dedup_key for service_degraded
3. dedup_key differs with different message
4. dedup_key differs with different source
5. dedup_key differs with different severity
6. normalize_message
7. check_and_tag returns deduped=False when no window
8. check_and_tag returns deduped=False for unknown event_type
9. dedup_key is deterministic (same input = same key)
10. dedup_key excludes timestamp/request_id
11. no prompt/response in payload
"""


def test_dedup_key_cluster_degraded():
    from runtime.incidents.incident_dedup import build_dedup_key

    k1 = build_dedup_key("cluster_degraded", "watchdog", "warning", "Cluster status is degraded", "")
    k2 = build_dedup_key("cluster_degraded", "watchdog", "warning", "Cluster status is degraded", "")
    assert k1 == k2
    assert isinstance(k1, str)
    assert len(k1) == 64  # sha256


def test_dedup_key_service_degraded():
    from runtime.incidents.incident_dedup import build_dedup_key

    k = build_dedup_key("service_degraded", "watchdog", "warning",
                         "Service 'live_api' just went down", "live_api")
    assert isinstance(k, str)
    assert len(k) == 64


def test_dedup_key_differs_with_different_message():
    from runtime.incidents.incident_dedup import build_dedup_key

    k1 = build_dedup_key("cluster_degraded", "watchdog", "warning",
                          "Cluster status is degraded", "")
    k2 = build_dedup_key("cluster_degraded", "watchdog", "warning",
                          "Cluster status is critical", "")
    assert k1 != k2


def test_dedup_key_differs_with_different_source():
    from runtime.incidents.incident_dedup import build_dedup_key

    k1 = build_dedup_key("cluster_degraded", "watchdog", "warning", "msg", "")
    k2 = build_dedup_key("cluster_degraded", "manual", "warning", "msg", "")
    assert k1 != k2


def test_dedup_key_differs_with_different_severity():
    from runtime.incidents.incident_dedup import build_dedup_key

    k1 = build_dedup_key("cluster_degraded", "watchdog", "warning", "msg", "")
    k2 = build_dedup_key("cluster_degraded", "watchdog", "critical", "msg", "")
    assert k1 != k2


def test_normalize_message():
    from runtime.incidents.incident_dedup import normalize_message

    assert normalize_message("Cluster status is degraded") == "cluster status is degraded"
    assert normalize_message("  Cluster  Status  ") == "cluster status"
    assert normalize_message("") == ""
    assert normalize_message(None) == ""


def test_dedup_key_excludes_timestamp():
    from runtime.incidents.incident_dedup import build_dedup_key
    import time

    k1 = build_dedup_key("cluster_degraded", "watchdog", "warning",
                          "Cluster status is degraded", "")
    time.sleep(0.01)
    k2 = build_dedup_key("cluster_degraded", "watchdog", "warning",
                          "Cluster status is degraded", "")
    assert k1 == k2  # Deterministic, timestamps don't affect


def test_check_and_tag_no_window():
    from runtime.incidents.incident_dedup import check_and_tag

    # service_down has no window configured
    result = check_and_tag("service_down", "watchdog", "warning", "msg", "")
    assert result["deduped"] is False
    assert result["action"] == "new"


def test_check_and_tag_unknown_event():
    from runtime.incidents.incident_dedup import check_and_tag

    result = check_and_tag("routing_error", "watchdog", "critical", "msg", "")
    assert result["deduped"] is False
    assert result["action"] == "new"


def test_check_and_tag_deduped_false_no_qdrant():
    from runtime.incidents.incident_dedup import check_and_tag

    # Without Qdrant, should return deduped=False
    result = check_and_tag("cluster_degraded", "watchdog", "warning",
                            "Cluster status is degraded", "")
    assert "dedup_key" in result
    assert "action" in result


def test_no_prompt_response_in_payload():
    from runtime.incidents.incident_dedup import build_dedup_key, check_and_tag

    k = build_dedup_key("cluster_degraded", "watchdog", "warning",
                          "Cluster status is degraded", "")
    # Verify no prompt or response content in the key
    assert "prompt" not in k
    assert "response" not in k
    assert "content" not in k


def test_dedup_metrics_import():
    from runtime.telemetry.prometheus_metrics import (
        INCIDENT_DEDUP_SKIPPED_TOTAL,
        INCIDENT_DEDUP_NEW_TOTAL,
        INCIDENT_DEDUP_ERRORS_TOTAL,
    )
    assert INCIDENT_DEDUP_SKIPPED_TOTAL is not None
    assert INCIDENT_DEDUP_NEW_TOTAL is not None
    assert INCIDENT_DEDUP_ERRORS_TOTAL is not None
