"""FASE 37A: Cognitive Health Layer tests.

Focus:
- bounded, deterministic, fail-safe APIs
- bounded latency store behavior
- prometheus text renderer shape
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_latency_store_is_bounded_and_computable() -> None:
    from runtime.telemetry.gateway_metrics import get_latency_stats, record_latency_sample

    # Seed a deterministic sequence
    for i in range(300):
        record_latency_sample(float(i), kind="request_total", route_family="test", model="m")

    stats = get_latency_stats(kind="request_total", route_family="test", model="m")
    assert stats["count"] <= 256
    assert stats["max_ms"] >= 255
    assert stats["p50_ms"] >= 100
    assert stats["p95_ms"] >= 200


def test_health_snapshot_is_fail_safe() -> None:
    from runtime.health.cognitive_health_layer import build_cognitive_health_snapshot

    snap = build_cognitive_health_snapshot(window_minutes=60)
    assert isinstance(snap, dict)
    assert snap.get("contract_version") == "37A-COGNITIVE-HEALTH-LAYER-01"
    assert snap.get("status") in ("ok", "degraded")
    assert "score" in snap
    assert "routing_confidence" in snap
    assert "watchdog" in snap


def test_prometheus_metrics_renderer_is_present() -> None:
    from runtime.health.cognitive_health_layer import build_cognitive_health_prometheus_metrics

    text = build_cognitive_health_prometheus_metrics()
    assert "ailab_cognitive_health_score" in text
    assert "ailab_cognitive_health_routing_confidence" in text
    assert "ailab_cognitive_health_nodes_online" in text
    assert "ailab_gateway_latency_p95_ms" in text


def test_degradations_snapshot_is_bounded_and_deterministic() -> None:
    from runtime.health.cognitive_health_layer import build_degradations_snapshot

    snap = build_degradations_snapshot(window_minutes=60)
    assert snap.get("contract_version") == "37A-COGNITIVE-HEALTH-LAYER-01"
    assert snap.get("status") in ("ok", "degraded")
    assert isinstance(snap.get("degradations"), list)
    assert isinstance(snap.get("offline_nodes"), list)
    assert isinstance(snap.get("degraded_nodes"), list)
    assert len(snap.get("offline_nodes")) <= 20
    assert len(snap.get("degraded_nodes")) <= 20


def test_build_node_scores_reconciles_history_with_control_plane_aliases(monkeypatch) -> None:
    import runtime.health.cognitive_health_layer as ch

    def _fake_control_nodes() -> dict:
        return {
            "nodes": {
                "192.168.1.50": {
                    "online": True,
                    "host": "rx9070",
                    "models": 3,
                    "avg_latency_ms": 10,
                }
            }
        }

    def _fake_stats_by_node(*, window_minutes: int = 60) -> dict:
        return {
            "rx9070": {
                "total_requests": 12,
                "success_rate": 1.0,
                "avg_latency_ms": 1200,
                "last_updated": 123,
            }
        }

    monkeypatch.setattr("runtime.control.control_plane.get_control_nodes", _fake_control_nodes)
    monkeypatch.setattr("runtime.routing.routing_history.stats_by_node", _fake_stats_by_node)

    nodes = ch.build_node_scores(window_minutes=60)
    assert len(nodes) == 1
    assert nodes[0].node == "192.168.1.50"
    assert nodes[0].online is True
    assert nodes[0].stats.get("success_rate") == 1.0


def test_build_node_scores_reconciles_history_with_backend_aliases(monkeypatch) -> None:
    import runtime.health.cognitive_health_layer as ch

    def _fake_control_nodes() -> dict:
        return {
            "nodes": {
                "192.168.1.50": {
                    "online": True,
                    "host": "192.168.1.50",
                    "models": 3,
                    "avg_latency_ms": 10,
                }
            }
        }

    def _fake_stats_by_node(*, window_minutes: int = 60) -> dict:
        return {
            "rx9070": {
                "total_requests": 6,
                "success_rate": 1.0,
                "avg_latency_ms": 900,
                "last_updated": 321,
            }
        }

    monkeypatch.setattr("runtime.control.control_plane.get_control_nodes", _fake_control_nodes)
    monkeypatch.setattr("runtime.routing.routing_history.stats_by_node", _fake_stats_by_node)
    monkeypatch.setattr(ch, "_build_backend_host_aliases", lambda: {"192.168.1.50": {"rx9070"}})

    nodes = ch.build_node_scores(window_minutes=60)
    assert len(nodes) == 1
    assert nodes[0].node == "192.168.1.50"
    assert nodes[0].stats.get("success_rate") == 1.0
