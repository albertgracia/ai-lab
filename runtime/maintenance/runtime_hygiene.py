"""FASE 27.2: Runtime hygiene — inspeccion sin cambios automaticos.

Verifica rotacion de audit shards, cardinalidad Prometheus,
dashboards huerfanos y uso de metricas.

NUNCA borra datos sin flag explicita (dry_run=True por defecto).
"""

from __future__ import annotations

import json
from datetime import datetime as _dt
from pathlib import Path

_AUDIT_BASE = Path("/opt/ai-lab/runtime/state")


def check_audit_rotation() -> dict:
    """Verifica que los shards diarios existen y su tamano."""
    today = _dt.now().strftime("%Y-%m-%d")
    shards = sorted(_AUDIT_BASE.glob("governance_audit-*.jsonl"))
    result = {
        "shards": len(shards),
        "today": today,
        "active_shard": f"governance_audit-{today}.jsonl",
        "active_exists": (_AUDIT_BASE / f"governance_audit-{today}.jsonl").exists(),
    }
    sizes = []
    for s in shards:
        try:
            size = s.stat().st_size
            sizes.append({"name": s.name, "size_bytes": size})
        except Exception:
            pass
    result["shard_sizes"] = sizes
    result["total_bytes"] = sum(s.get("size_bytes", 0) for s in sizes)
    return result


def check_dashboard_health() -> dict:
    """Inspecciona dashboards provisionados en busca de paneles sin datos."""
    base = Path("/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB")
    dashboards = []
    for f in sorted(base.glob("*.json")):
        try:
            d = json.loads(f.read_text())
            dashboards.append({
                "uid": d.get("uid", "?"),
                "title": d.get("title", "?"),
                "panels": len(d.get("panels", [])),
            })
        except Exception:
            pass
    return {"count": len(dashboards), "dashboards": dashboards}


def summarize_metrics_usage() -> dict:
    """Resumen del uso de metricas — cuantas series activas."""
    try:
        from prometheus_client import REGISTRY
        metrics = []
        for metric in REGISTRY.collect():
            samples = list(metric.samples)
            if samples:
                metrics.append({
                    "name": metric.name,
                    "type": metric.type,
                    "samples": len(samples),
                    "labels": list(samples[0].labels.keys()) if samples else [],
                })
        return {"total_metrics": len(metrics), "metrics": metrics}
    except ImportError:
        return {"error": "prometheus_client not available"}


def cleanup_old_audit_shards(days: int = 90, dry_run: bool = True) -> dict:
    """Elimina shards de auditoria mas antiguos que *days*.

    SOLO si dry_run=False.
    """
    from datetime import datetime as _dt, timedelta
    cutoff = _dt.now() - timedelta(days=days)
    removed = []
    for shard in _AUDIT_BASE.glob("governance_audit-*.jsonl"):
        try:
            date_str = shard.name.replace("governance_audit-", "").replace(".jsonl", "")
            shard_date = _dt.strptime(date_str, "%Y-%m-%d")
            if shard_date < cutoff:
                removed.append({"name": shard.name, "date": date_str})
                if not dry_run:
                    shard.unlink()
        except Exception:
            pass
    return {"dry_run": dry_run, "removed": len(removed), "shards": removed}
