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
