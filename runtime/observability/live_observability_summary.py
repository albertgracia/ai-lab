"""Live observability fact summary.

Produced by observability so performance/reporting can consume observability
state without routing through the reporting bounded context.
"""

from __future__ import annotations

from typing import Any


def build_live_observability_summary(
    extra_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Expose live observability diagnostics as a compact fact summary."""
    extra_ctx = extra_ctx or {}
    try:
        from runtime.observability import run_live_observability_diagnostics

        rep = run_live_observability_diagnostics(extra_ctx=extra_ctx)
        score = rep.get("score", {}) or {}
        incidents = rep.get("incidents", {}) or {}
        staleness = rep.get("authority_staleness", {}) or {}
        exporters = rep.get("exporters", {}) or {}
        scrape = rep.get("scrape", {}) or {}

        return {
            "contract_version": rep.get("contract_version", "OBS-34B"),
            "live_observability_score": score.get("live_observability_score", 0.0),
            "live_observability_level": score.get("live_observability_level", "unknown"),
            "highest_incident_severity": incidents.get("highest_severity", "info"),
            "incidents_total": incidents.get("incidents_total", 0),
            "authority_freshness": staleness.get("authority_freshness", "unknown"),
            "scrape_failures_total": scrape.get("scrape_failures_total", 0),
            "exporter_unreachable_total": (exporters.get("summary", {}) or {}).get("unreachable_total", 0),
            "exporter_flapping_total": (((exporters.get("summary", {}) or {}).get("flapping", {}) or {}).get("flapping_total", 0)),
            "deterministic_signature": rep.get("deterministic_signature"),
        }
    except Exception as exc:
        return {
            "contract_version": "OBS-34B",
            "live_observability_score": 0.0,
            "live_observability_level": "unknown",
            "incidents_total": 0,
            "authority_freshness": "unknown",
            "error": str(exc),
        }
