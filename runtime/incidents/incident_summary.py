"""Incident state summaries.

Facts produced by the incidents bounded context. Reporting may consume these,
but incidents/fastpath/precision should not depend on reporting for incident
state.
"""

from __future__ import annotations

from typing import Any


def build_incident_intelligence_summary(
    *,
    extra_ctx: dict[str, Any] | None = None,
    sensor_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """FASE 36A: compact incident intelligence summary."""
    extra_ctx = extra_ctx or {}
    sensor_snapshot = sensor_snapshot or {}
    try:
        from runtime.incidents import build_incident_intelligence_report

        rep = build_incident_intelligence_report(extra_ctx=extra_ctx, sensor_snapshot=sensor_snapshot)

        codebase_enrichment: dict[str, Any] = {}
        try:
            from runtime.codebase import build_codebase_summary, build_codebase_ownership

            cb = build_codebase_summary(extra_ctx=extra_ctx)
            co = build_codebase_ownership(extra_ctx=extra_ctx)
            codebase_enrichment = {
                "structural_health_score": (cb.get("score", {}) or {}).get("structural_health_score", 0.0),
                "structural_health_level": (cb.get("score", {}) or {}).get("level", "unknown"),
                "modules_total": (cb.get("score", {}) or {}).get("modules_total", 0),
                "ownership_domains": co.get("domains_total", 0),
                "hotspots": (cb.get("summary", {}) or {}).get("hotspots", []),
            }
        except Exception:
            codebase_enrichment = {"error": "codebase module unavailable"}

        return {
            "contract_version": "36A",
            "incidents": {
                "active_incidents_total": rep.get("incident_count", 0),
                "highest_severity": rep.get("highest_severity", "info"),
                "affected_domains": rep.get("affected_domains", []),
            },
            "blast_radius": rep.get("blast_radius_summary", {}),
            "correlations_total": len(rep.get("correlation_results", []) or []),
            "recommendations_total": rep.get("recommendations_total", 0),
            "codebase": codebase_enrichment,
            "deterministic_signature": rep.get("deterministic_signature"),
        }
    except Exception as exc:
        return {
            "contract_version": "36A",
            "incidents": {"active_incidents_total": 0, "highest_severity": "unknown", "affected_domains": []},
            "codebase": {"error": str(exc)},
        }
