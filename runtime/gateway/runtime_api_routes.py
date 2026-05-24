"""Gateway runtime API route handlers.

Purpose: keep openai_gateway.py lighter by grouping runtime API endpoints into
small, import-light entrypoints.

This file must remain safe to import: domain-heavy imports are done lazily
inside handler functions.
"""

from __future__ import annotations

import time
from typing import Any


def handle_fastpath_routes(handler: Any) -> bool:
    """Handle /runtime/fastpath* endpoints.

    Returns True if the request was handled (a response was sent).
    """
    path = getattr(handler, "path", "")
    if not (path == "/runtime/fastpath" or path.startswith("/runtime/fastpath/")):
        return False

    try:
        from runtime.fastpath import (
            build_fastpath_response,
            build_fast_operational_summary,
            build_fast_observability_summary,
            build_fast_governance_summary,
            build_fast_validation_summary,
            build_fast_topology_summary,
            build_fast_infrastructure_summary,
            build_fast_gpu_summary,
            get_fastpath_cache_state,
            prime_fastpath_cache,
        )

        if path == "/runtime/fastpath" or path == "/runtime/fastpath/score":
            resp = build_fastpath_response(
                "estado runtime",
                extra_ctx={"enable_network": False},
                sensor_snapshot={},
                verbosity="operational",
            )
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "35D",
                "fastpath": resp,
                "cache": get_fastpath_cache_state(),
            })
            return True

        if path == "/runtime/fastpath/cache":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/cache",
                "timestamp": time.time(),
                "contract_version": "35D",
                "cache": get_fastpath_cache_state(),
                "primed": prime_fastpath_cache(extra_ctx={"enable_network": False}),
            })
            return True

        if path == "/runtime/fastpath/operational":
            auth = None
            try:
                from runtime.fastpath.operational_fastpath import _build_fastpath_authority_snapshot

                auth = _build_fastpath_authority_snapshot(extra_ctx={"enable_network": False})
            except Exception:
                auth = None
            summ = build_fast_operational_summary(extra_ctx={"verbosity": "operational"}, authority=auth)
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/operational",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/observability":
            summ = build_fast_observability_summary(extra_ctx={"verbosity": "operational"})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/observability",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/governance":
            summ = build_fast_governance_summary(extra_ctx={"verbosity": "operational"}, sensor_snapshot={})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/governance",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/validation":
            summ = build_fast_validation_summary(extra_ctx={"verbosity": "operational"}, sensor_snapshot={})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/validation",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/topology":
            summ = build_fast_topology_summary(extra_ctx={"verbosity": "operational"})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/topology",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/infrastructure":
            summ = build_fast_infrastructure_summary(extra_ctx={"verbosity": "operational"})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/infrastructure",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        if path == "/runtime/fastpath/gpu":
            summ = build_fast_gpu_summary(extra_ctx={"verbosity": "operational"})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/fastpath/gpu",
                "timestamp": time.time(),
                "contract_version": "35D",
                "summary": summ,
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "35D",
            "error": "unknown_fastpath_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "35D",
            "error": str(exc),
        })
        return True


def handle_incidents_routes(handler: Any) -> bool:
    """Handle /runtime/incidents* endpoints."""
    path = getattr(handler, "path", "")
    if not (path == "/runtime/incidents" or path.startswith("/runtime/incidents/")):
        return False

    try:
        from runtime.incidents import build_incident_intelligence_report
        from runtime.telemetry.prometheus_metrics import record_incident_intelligence_metrics

        if path == "/runtime/incidents" or path == "/runtime/incidents/report":
            rep = build_incident_intelligence_report(extra_ctx={}, sensor_snapshot={})
            try:
                record_incident_intelligence_metrics(rep)
            except Exception:
                pass
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "36A",
                "incident_report": rep,
            })
            return True

        if path == "/runtime/incidents/active":
            rep = build_incident_intelligence_report(extra_ctx={}, sensor_snapshot={})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/incidents/active",
                "timestamp": time.time(),
                "contract_version": "36A",
                "active_incidents": rep.get("active_incidents", []),
                "incident_count": rep.get("incident_count", 0),
                "highest_severity": rep.get("highest_severity", "info"),
            })
            return True

        if path == "/runtime/incidents/correlations":
            rep = build_incident_intelligence_report(extra_ctx={}, sensor_snapshot={})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/incidents/correlations",
                "timestamp": time.time(),
                "contract_version": "36A",
                "correlation_results": rep.get("correlation_results", []),
            })
            return True

        if path == "/runtime/incidents/blast-radius":
            rep = build_incident_intelligence_report(extra_ctx={}, sensor_snapshot={})
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/incidents/blast-radius",
                "timestamp": time.time(),
                "contract_version": "36A",
                "blast_radius_summary": rep.get("blast_radius_summary", {}),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "36A",
            "error": "unknown_incidents_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "36A",
            "error": str(exc),
        })
        return True


def handle_health_routes(handler: Any) -> bool:
    """Handle /runtime/health* endpoints (FASE 37A).

    Always responds 200; fail-safe.
    """
    raw = getattr(handler, "path", "")
    path = (raw or "").split("?", 1)[0]
    if not (path == "/runtime/health" or path.startswith("/runtime/health/")):
        return False

    try:
        from runtime.health.cognitive_health_layer import build_cognitive_health_snapshot, build_degradations_snapshot

        if path in ("/runtime/health", "/runtime/health/score", "/runtime/health/summary"):
            handler._send_json(200, build_cognitive_health_snapshot(window_minutes=60))
            return True

        if path == "/runtime/health/nodes":
            snap = build_cognitive_health_snapshot(window_minutes=60)
            handler._send_json(200, {
                "status": snap.get("status", "ok"),
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/health/nodes",
                "timestamp": time.time(),
                "contract_version": snap.get("contract_version"),
                "nodes": snap.get("nodes", []),
                "nodes_total": snap.get("nodes_total", 0),
                "nodes_online": snap.get("nodes_online", 0),
            })
            return True

        if path == "/runtime/health/routing-confidence":
            snap = build_cognitive_health_snapshot(window_minutes=60)
            handler._send_json(200, {
                "status": snap.get("status", "ok"),
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/health/routing-confidence",
                "timestamp": time.time(),
                "contract_version": snap.get("contract_version"),
                "routing_confidence": snap.get("routing_confidence", {}),
            })
            return True

        if path == "/runtime/health/watchdog":
            snap = build_cognitive_health_snapshot(window_minutes=60)
            handler._send_json(200, {
                "status": snap.get("status", "ok"),
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/health/watchdog",
                "timestamp": time.time(),
                "contract_version": snap.get("contract_version"),
                "watchdog": snap.get("watchdog", {}),
            })
            return True

        if path == "/runtime/health/latency":
            try:
                from runtime.telemetry.gateway_metrics import get_latency_stats
                total = get_latency_stats(kind="request_total")
                ttfb = get_latency_stats(kind="ttfb")
            except Exception:
                total = {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "last_ms": 0.0}
                ttfb = {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0, "last_ms": 0.0}
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/health/latency",
                "timestamp": time.time(),
                "contract_version": "37A-COGNITIVE-HEALTH-LAYER-01",
                "latency": {
                    "request_total": total,
                    "ttfb": ttfb,
                },
            })
            return True

        if path == "/runtime/health/degradations":
            handler._send_json(200, build_degradations_snapshot(window_minutes=60))
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "37A-COGNITIVE-HEALTH-LAYER-01",
            "error": "unknown_health_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "37A-COGNITIVE-HEALTH-LAYER-01",
            "error": str(exc),
        })
        return True


def handle_correlation_routes(handler: Any) -> bool:
    """Handle /runtime/correlation* endpoints (FASE 37B).

    Always responds 200; bounded + deterministic; fail-safe.
    """
    raw = getattr(handler, "path", "")
    path = (raw or "").split("?", 1)[0]
    if not (path == "/runtime/correlation" or path.startswith("/runtime/correlation/")):
        return False

    try:
        from runtime.correlation.graph_runtime_correlation import (
            build_graph_runtime_correlation_snapshot,
            get_graph_runtime_correlation_summary,
            get_correlated_hotspots,
            get_correlated_blast_radius,
            get_runtime_topology_findings,
            get_correlation_recommendations,
            reset_graph_runtime_correlation_state,
            GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
        )

        if path == "/runtime/correlation" or path == "/runtime/correlation/summary":
            payload = build_graph_runtime_correlation_snapshot() if path == "/runtime/correlation" else get_graph_runtime_correlation_summary()
            handler._send_json(200, payload)
            return True

        if path == "/runtime/correlation/hotspots":
            handler._send_json(200, get_correlated_hotspots())
            return True

        if path == "/runtime/correlation/blast-radius":
            handler._send_json(200, get_correlated_blast_radius())
            return True

        if path == "/runtime/correlation/findings":
            handler._send_json(200, get_runtime_topology_findings())
            return True

        if path == "/runtime/correlation/recommendations":
            handler._send_json(200, get_correlation_recommendations())
            return True

        if path == "/runtime/correlation/reset":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/correlation/reset",
                "timestamp": time.time(),
                "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
                "reset": reset_graph_runtime_correlation_state(),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": GRAPH_RUNTIME_CORRELATION_CONTRACT_VERSION,
            "error": "unknown_correlation_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "37B-GRAPH-RUNTIME-CORRELATION-01",
            "error": str(exc),
        })
        return True


def handle_critical_path_routes(handler: Any) -> bool:
    """Handle /runtime/critical-path* endpoints (FASE 37C).

    Always responds 200; bounded + deterministic; fail-safe.
    """
    raw = getattr(handler, "path", "")
    path = (raw or "").split("?", 1)[0]
    if not (path == "/runtime/critical-path" or path.startswith("/runtime/critical-path/")):
        return False

    import urllib.parse

    try:
        from runtime.critical_path.critical_path_analysis import (
            build_critical_path_snapshot,
            get_critical_path_summary,
            get_critical_path_modules,
            get_critical_path_routes,
            get_critical_path_dependencies,
            get_critical_path_recommendations,
            reset_critical_path_state,
            CRITICAL_PATH_CONTRACT_VERSION,
        )

        parsed = urllib.parse.urlparse(raw)
        qs = urllib.parse.parse_qs(parsed.query or "")

        if path == "/runtime/critical-path":
            top_n = int((qs.get("top_n") or [10])[0])
            handler._send_json(200, build_critical_path_snapshot(top_n=top_n))
            return True

        if path == "/runtime/critical-path/summary":
            handler._send_json(200, get_critical_path_summary())
            return True

        if path == "/runtime/critical-path/modules":
            top_n = int((qs.get("top_n") or [10])[0])
            handler._send_json(200, get_critical_path_modules(top_n=top_n))
            return True

        if path == "/runtime/critical-path/routes":
            handler._send_json(200, get_critical_path_routes())
            return True

        if path == "/runtime/critical-path/dependencies":
            file_path = str((qs.get("file") or qs.get("file_path") or [""])[0])
            handler._send_json(200, get_critical_path_dependencies(file_path=file_path))
            return True

        if path == "/runtime/critical-path/recommendations":
            handler._send_json(200, get_critical_path_recommendations())
            return True

        if path == "/runtime/critical-path/reset":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/critical-path/reset",
                "timestamp": time.time(),
                "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
                "reset": reset_critical_path_state(),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": CRITICAL_PATH_CONTRACT_VERSION,
            "error": "unknown_critical_path_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "37C-CRITICAL-PATH-ANALYSIS-01",
            "error": str(exc),
        })
        return True


def handle_evidence_routes(handler: Any) -> bool:
    """Handle /runtime/evidence* endpoints (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/evidence" or path.startswith("/runtime/evidence/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 10
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 10

        from runtime.federation.federation_observability import (
            get_evidence_hotspots,
            get_evidence_lineage,
            get_evidence_summary,
            get_lineage_hotspots,
        )

        if clean_path == "/runtime/evidence" or clean_path == "/runtime/evidence/summary":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "EVID-01",
                "summary": get_evidence_summary(),
            })
            return True

        if clean_path == "/runtime/evidence/hotspots":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/evidence/hotspots",
                "timestamp": time.time(),
                "contract_version": "EVID-01",
                "hotspots": get_evidence_hotspots(limit=limit),
                "lineage_hotspots": get_lineage_hotspots(min_events=3),
            })
            return True

        if clean_path.startswith("/runtime/evidence/lineage/"):
            evidence_id = clean_path.split("/runtime/evidence/lineage/", 1)[1]
            # Basic validation: bounded length and hex-ish.
            evidence_id = (evidence_id or "").strip()
            if not evidence_id or len(evidence_id) > 64:
                handler._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/evidence/lineage",
                    "timestamp": time.time(),
                    "contract_version": "EVID-01",
                    "error": "invalid_evidence_id",
                })
                return True

            hit = get_evidence_lineage(evidence_id)
            if not hit:
                handler._send_json(200, {
                    "status": "degraded",
                    "service": "ai-lab-openai-gateway",
                    "endpoint": "runtime/evidence/lineage",
                    "timestamp": time.time(),
                    "contract_version": "EVID-01",
                    "evidence_id": evidence_id,
                    "found": False,
                })
                return True

            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/evidence/lineage",
                "timestamp": time.time(),
                "contract_version": "EVID-01",
                "evidence_id": evidence_id,
                "found": True,
                "lineage": hit,
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "EVID-01",
            "error": "unknown_evidence_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/evidence",
            "timestamp": time.time(),
            "contract_version": "EVID-01",
            "error": str(exc),
        })
        return True


def handle_guard_routes(handler: Any) -> bool:
    """Handle /runtime/guards* endpoints (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/guards" or path.startswith("/runtime/guards/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 50
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 50

        from runtime.federation.federation_guards import (
            get_federation_guard_events,
            get_federation_guard_runtime_state,
            get_federation_guard_summary,
        )

        if clean_path == "/runtime/guards" or clean_path == "/runtime/guards/summary":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "CG-01",
                "summary": get_federation_guard_summary(),
            })
            return True

        if clean_path == "/runtime/guards/state":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/guards/state",
                "timestamp": time.time(),
                "contract_version": "CG-01",
                "state": get_federation_guard_runtime_state(),
            })
            return True

        if clean_path == "/runtime/guards/events":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/guards/events",
                "timestamp": time.time(),
                "contract_version": "CG-01",
                "events": get_federation_guard_events(limit=limit),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "CG-01",
            "error": "unknown_guards_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/guards",
            "timestamp": time.time(),
            "contract_version": "CG-01",
            "error": str(exc),
        })
        return True


def handle_model_registry_routes(handler: Any) -> bool:
    """Handle /runtime/models/registry endpoint (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/models/registry" or path.startswith("/runtime/models/registry/")):
        return False

    try:
        from runtime.models.model_registry import build_public_registry_snapshot

        handler._send_json(200, {
            "status": "ok",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/models/registry",
            "timestamp": time.time(),
            "contract_version": "MODEL-REGISTRY-CANONICAL-01",
            "registry": build_public_registry_snapshot(),
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/models/registry",
            "timestamp": time.time(),
            "contract_version": "MODEL-REGISTRY-CANONICAL-01",
            "error": str(exc),
        })
        return True


def handle_slo_routes(handler: Any) -> bool:
    """Handle /runtime/slo* endpoints (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/slo" or path.startswith("/runtime/slo/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 50
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 50

        from runtime.slo.cognitive_slo import get_slo_summary, get_slo_status, get_slo_violations

        if clean_path == "/runtime/slo" or clean_path == "/runtime/slo/summary":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "SLO-01",
                "slo_summary": get_slo_summary(),
            })
            return True

        if clean_path == "/runtime/slo/status":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/slo/status",
                "timestamp": time.time(),
                "contract_version": "SLO-01",
                "slo_status": get_slo_status(),
            })
            return True

        if clean_path == "/runtime/slo/violations":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/slo/violations",
                "timestamp": time.time(),
                "contract_version": "SLO-01",
                "slo_violations": get_slo_violations(limit=limit),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "SLO-01",
            "error": "unknown_slo_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/slo",
            "timestamp": time.time(),
            "contract_version": "SLO-01",
            "error": str(exc),
        })
        return True


def handle_architecture_routes(handler: Any) -> bool:
    """Handle /runtime/architecture* endpoints (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/architecture" or path.startswith("/runtime/architecture/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 20
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 20

        from runtime.governance.architecture_governance import (
            get_architecture_summary,
            get_architecture_hotspots,
            get_architecture_violations,
        )

        if clean_path == "/runtime/architecture" or clean_path == "/runtime/architecture/summary":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": "ARCH-01",
                "architecture": get_architecture_summary(),
            })
            return True

        if clean_path == "/runtime/architecture/hotspots":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/architecture/hotspots",
                "timestamp": time.time(),
                "contract_version": "ARCH-01",
                "hotspots": get_architecture_hotspots(limit=limit),
            })
            return True

        if clean_path == "/runtime/architecture/violations":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/architecture/violations",
                "timestamp": time.time(),
                "contract_version": "ARCH-01",
                "violations": get_architecture_violations(limit=limit),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": "ARCH-01",
            "error": "unknown_architecture_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/architecture",
            "timestamp": time.time(),
            "contract_version": "ARCH-01",
            "error": str(exc),
        })
        return True


def handle_graph_routes(handler: Any) -> bool:
    """Handle /runtime/graph* endpoints (read-only, fail-safe)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/graph" or path.startswith("/runtime/graph/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 20
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 20

        from runtime.graph_reasoning.gitnexus_graph_reasoning import (
            get_graph_reasoning_summary,
            get_graph_hotspots,
            get_graph_blast_radius,
            get_graph_governance_findings,
            get_graph_correlations,
            get_graph_metrics,
            record_graph_metrics,
            reset_graph_reasoning_state,
            GRAPH_CONTRACT_VERSION,
        )

        if clean_path == "/runtime/graph" or clean_path == "/runtime/graph/summary":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "graph_summary": get_graph_reasoning_summary(),
            })
            return True

        if clean_path == "/runtime/graph/hotspots":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/hotspots",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "hotspots": get_graph_hotspots(),
            })
            record_graph_metrics()
            return True

        if clean_path == "/runtime/graph/blast-radius":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/blast-radius",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "blast_radius": get_graph_blast_radius(),
            })
            return True

        if clean_path == "/runtime/graph/governance":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/governance",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "governance_findings": get_graph_governance_findings(),
            })
            return True

        if clean_path == "/runtime/graph/correlations":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/correlations",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "correlations": get_graph_correlations(),
            })
            return True

        if clean_path == "/runtime/graph/metrics":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/metrics",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "graph_metrics": get_graph_metrics(),
            })
            return True

        if clean_path == "/runtime/graph/reset":
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/graph/reset",
                "timestamp": time.time(),
                "contract_version": GRAPH_CONTRACT_VERSION,
                "reset": reset_graph_reasoning_state(),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": GRAPH_CONTRACT_VERSION,
            "error": "unknown_graph_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/graph",
            "timestamp": time.time(),
            "contract_version": GRAPH_CONTRACT_VERSION,
            "error": str(exc),
        })
        return True


def handle_triage_routes(handler: Any) -> bool:
    """Handle /runtime/triage* endpoints (read-only, fail-safe, always-on 200)."""

    path = getattr(handler, "path", "")
    if not (path == "/runtime/triage" or path.startswith("/runtime/triage/")):
        return False

    import urllib.parse

    try:
        parsed = urllib.parse.urlparse(path)
        clean_path = parsed.path
        qs = urllib.parse.parse_qs(parsed.query or "")
        limit = 20
        try:
            if "limit" in qs and qs["limit"]:
                limit = int(qs["limit"][0])
        except Exception:
            limit = 20

        from runtime.triage.autonomous_triage import (
            build_runtime_triage_snapshot,
            get_active_triage_incidents,
            get_triage_summary,
            get_triage_recommendations,
            get_triage_snapshots,
            record_triage_metrics,
            TRIAGE_CONTRACT_VERSION,
        )

        if clean_path == "/runtime/triage" or clean_path == "/runtime/triage/snapshot":
            snapshot = build_runtime_triage_snapshot()
            record_triage_metrics()
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": clean_path.lstrip("/"),
                "timestamp": time.time(),
                "contract_version": TRIAGE_CONTRACT_VERSION,
                "triage_snapshot": snapshot,
            })
            return True

        if clean_path == "/runtime/triage/summary":
            record_triage_metrics()
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/triage/summary",
                "timestamp": time.time(),
                "contract_version": TRIAGE_CONTRACT_VERSION,
                "triage_summary": get_triage_summary(),
            })
            return True

        if clean_path == "/runtime/triage/incidents":
            record_triage_metrics()
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/triage/incidents",
                "timestamp": time.time(),
                "contract_version": TRIAGE_CONTRACT_VERSION,
                "incidents": get_active_triage_incidents(),
                "total": len(get_active_triage_incidents()),
            })
            return True

        if clean_path == "/runtime/triage/recommendations":
            record_triage_metrics()
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/triage/recommendations",
                "timestamp": time.time(),
                "contract_version": TRIAGE_CONTRACT_VERSION,
                "recommendations": get_triage_recommendations(),
                "total": len(get_triage_recommendations()),
            })
            return True

        if clean_path == "/runtime/triage/snapshots":
            snapshots = get_triage_snapshots(limit=limit)
            handler._send_json(200, {
                "status": "ok",
                "service": "ai-lab-openai-gateway",
                "endpoint": "runtime/triage/snapshots",
                "timestamp": time.time(),
                "contract_version": TRIAGE_CONTRACT_VERSION,
                "snapshots": snapshots,
                "total": len(snapshots),
            })
            return True

        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": clean_path.lstrip("/"),
            "timestamp": time.time(),
            "contract_version": TRIAGE_CONTRACT_VERSION,
            "error": "unknown_triage_endpoint",
        })
        return True

    except Exception as exc:
        handler._send_json(200, {
            "status": "degraded",
            "service": "ai-lab-openai-gateway",
            "endpoint": "runtime/triage",
            "timestamp": time.time(),
            "contract_version": TRIAGE_CONTRACT_VERSION,
            "error": str(exc),
        })
        return True
