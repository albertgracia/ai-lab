"""Runtime Pattern Learning — detect operational patterns from Qdrant data.

Reads incidents, routing_history, and cognitive_history to identify:
  - Node failure patterns (frequency, recurrence, severity trends)
  - Latency degradation (per-model, per-node trends)
  - Context overflow patterns (budget spikes, timing)
  - Time-based clustering (failure windows, peak issue hours)
  - Model performance degradation (success rate + latency drift)
  - Recall quality degradation (contamination, noise)

Usage:
    from runtime.memory.pattern_learner import run_all
    patterns = run_all()
"""

import json
import time
from collections import Counter, defaultdict
from pathlib import Path


def run_all(days: int = 7) -> list[dict]:
    """Run every pattern detector and return ranked patterns.

    Sources: Qdrant incidents, routing_history.jsonl, cognitive_history.jsonl

    Each pattern:
        type: str          — pattern category
        target: str        — affected entity (model, node, profile, collection)
        severity: str      — critical/warning/info
        confidence: float  — 0.0-1.0
        evidence: str      — human-readable summary
        recommendation: str — suggested action
        details: dict      — supporting data
        timestamp: int     — when detected
    """
    patterns = []

    try:
        from runtime.memory.qdrant_store import scroll_all
    except ImportError:
        return [{"type": "error", "target": "qdrant", "severity": "critical", "confidence": 1.0, "evidence": "Qdrant store unavailable", "recommendation": "check Qdrant service", "details": {}, "timestamp": int(time.time())}]

    cutoff = time.time() - days * 86400

    # Qdrant sources
    incidents = scroll_all("incidents")
    incidents = [p for p in incidents if p["payload"].get("timestamp", 0) >= cutoff]

    # JSONL sources
    routing = _load_jsonl("/opt/ai-lab/runtime/state/routing_history.jsonl", cutoff)
    cognitive = _load_jsonl("/opt/ai-lab/runtime/state/cognitive_history.jsonl", cutoff)

    patterns.extend(_detect_node_failure_patterns(incidents))
    patterns.extend(_detect_severity_trends(incidents))
    patterns.extend(_detect_peak_hours(incidents))
    patterns.extend(_detect_context_budget_patterns(cognitive))
    patterns.extend(_detect_model_performance_trends(routing))
    patterns.extend(_detect_recall_quality_patterns(incidents, routing, cognitive))

    patterns.sort(key=lambda p: (-p["confidence"], p["severity"]))
    return patterns


def learn_patterns(days: int = 7) -> list[dict]:
    """Legacy wrapper — delegates to run_all."""
    return run_all(days)


def _load_jsonl(path: str, cutoff: float) -> list[dict]:
    """Load JSONL entries newer than cutoff."""
    f = Path(path)
    if not f.exists():
        return []
    records = []
    for line in f.read_text().strip().splitlines():
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("timestamp", 0) >= cutoff:
                records.append(rec)
        except json.JSONDecodeError:
            pass
    return records


def _detect_node_failure_patterns(incidents: list[dict]) -> list[dict]:
    """Detect nodes with repeated critical failures."""
    patterns = []
    node_failures: dict[str, list[dict]] = defaultdict(list)
    for p in incidents:
        p2 = p.get("payload", {})
        if p2.get("severity") in ("critical",) and p2.get("event_type") in ("node_failure", "node_offline"):
            node = p2.get("node", "unknown")
            node_failures[node].append(p2)

    for node, fails in node_failures.items():
        count = len(fails)
        if count >= 2:
            confidence = min(1.0, count / 5)
            warnings_only = [f for f in fails if f.get("severity") == "warning"]
            sev = "warning" if len(warnings_only) == count else "critical"
            patterns.append({
                "type": "repeated_node_failure",
                "target": node,
                "severity": sev,
                "confidence": round(confidence, 2),
                "evidence": f"Node {node} failed {count} times",
                "recommendation": "investigate node stability or deprioritize in routing",
                "details": {
                    "node": node,
                    "failure_count": count,
                    "event_types": list(set(f.get("event_type", "") for f in fails)),
                    "latest": max(f.get("timestamp", 0) for f in fails),
                },
                "timestamp": int(time.time()),
            })

    return patterns


def _detect_severity_trends(incidents: list[dict]) -> list[dict]:
    """Detect if critical incidents are trending up."""
    patterns = []
    severities = Counter(p.get("payload", {}).get("severity", "info") for p in incidents)

    total = sum(severities.values())
    if total < 3:
        return patterns

    critical_pct = severities.get("critical", 0) / total * 100
    if critical_pct > 30:
        patterns.append({
            "type": "high_critical_ratio",
            "target": "incidents",
            "severity": "critical",
            "confidence": round(min(1.0, critical_pct / 50), 2),
            "evidence": f"{critical_pct:.0f}% of incidents are critical ({severities['critical']}/{total})",
            "recommendation": "review critical alert thresholds and node health",
            "details": {
                "critical_pct": round(critical_pct, 1),
                "critical_count": severities.get("critical", 0),
                "total": total,
                "by_severity": dict(severities),
            },
            "timestamp": int(time.time()),
        })

    return patterns


def _detect_peak_hours(incidents: list[dict]) -> list[dict]:
    """Detect hours with most incidents (failure windows)."""
    patterns = []
    hour_counts: dict[int, int] = defaultdict(int)

    for p in incidents:
        ts = p.get("payload", {}).get("timestamp", 0)
        if ts:
            hour = time.gmtime(ts).tm_hour
            hour_counts[hour] += 1

    if not hour_counts:
        return patterns

    total = sum(hour_counts.values())
    peak_hour = max(hour_counts, key=hour_counts.get)
    peak_count = hour_counts[peak_hour]
    peak_pct = peak_count / total * 100

    if peak_pct > 20 and peak_count >= 2:
        patterns.append({
            "type": "peak_failure_hour",
            "target": f"utc_hour_{peak_hour}",
            "severity": "warning",
            "confidence": round(min(1.0, peak_pct / 40), 2),
            "evidence": f"Peak failures at UTC hour {peak_hour}:00 ({peak_count}/{total}, {peak_pct:.0f}%)",
            "recommendation": "consider pre-emptive checks before peak hour",
            "details": {
                "peak_hour_utc": peak_hour,
                "peak_count": peak_count,
                "total": total,
                "peak_pct": round(peak_pct, 1),
                "top_3_hours": sorted(hour_counts.items(), key=lambda x: -x[1])[:3],
            },
            "timestamp": int(time.time()),
        })

    return patterns


# ── New FASE 12 detectors ──────────────────────────────────────────────


def _detect_context_budget_patterns(cognitive: list[dict]) -> list[dict]:
    """Detect recurring high context budget usage per profile.

    Reads cognitive_history entries to find profiles where
    budget_used > 80% repeatedly.
    """
    patterns = []
    if not cognitive:
        return patterns

    profile_budgets: dict[str, list[float]] = defaultdict(list)
    for rec in cognitive:
        profile = rec.get("task_type", "general")
        bu = rec.get("budget_used", 0)
        if bu > 0:
            profile_budgets[profile].append(bu)

    for profile, budgets in profile_budgets.items():
        if len(budgets) < 3:
            continue
        high_count = sum(1 for b in budgets if b > 0.80)
        if high_count >= 3:
            avg_budget = sum(budgets) / len(budgets)
            confidence = min(1.0, high_count / max(len(budgets), 1) * 2)
            patterns.append({
                "type": "high_budget_recurring",
                "target": profile,
                "severity": "warning",
                "confidence": round(confidence, 2),
                "evidence": f"budget_used > 80% en {high_count} de {len(budgets)} cognitive snapshots para perfil {profile}",
                "recommendation": f"reduce recall max_chars para perfil {profile}",
                "details": {
                    "profile": profile,
                    "high_count": high_count,
                    "total_snapshots": len(budgets),
                    "avg_budget_used": round(avg_budget, 3),
                },
                "timestamp": int(time.time()),
            })

    # Detect recall bloat (recall_chars consistently high)
    profile_chars: dict[str, list[int]] = defaultdict(list)
    for rec in cognitive:
        profile = rec.get("task_type", "general")
        rc = rec.get("recall_chars", 0)
        if rc and rc > 500:
            profile_chars[profile].append(rc)

    for profile, chars in profile_chars.items():
        if len(chars) < 3:
            continue
        avg_chars = sum(chars) / len(chars)
        if avg_chars > 2000:
            patterns.append({
                "type": "recall_bloat",
                "target": profile,
                "severity": "warning",
                "confidence": round(min(1.0, avg_chars / 4000), 2),
                "evidence": f"recall_chars avg {avg_chars:.0f} para perfil {profile}",
                "recommendation": f"reduce recall max_chars para {profile} (actual: ~{avg_chars:.0f})",
                "details": {"profile": profile, "avg_recall_chars": round(avg_chars, 0)},
                "timestamp": int(time.time()),
            })

    return patterns


def _detect_model_performance_trends(routing: list[dict]) -> list[dict]:
    """Detect degrading or failing models from routing history."""
    patterns = []

    if not routing:
        return patterns

    # Group by model
    model_records: dict[str, list[dict]] = defaultdict(list)
    for rec in routing:
        model = rec.get("model", "unknown")
        model_records[model].append(rec)

    for model, records in model_records.items():
        if len(records) < 5:
            continue

        # Success rate
        successes = sum(1 for r in records if r.get("success", False))
        success_rate = successes / len(records)

        # Recent success rate (last 1/3)
        split = max(3, len(records) // 3)
        recent = records[-split:]
        recent_successes = sum(1 for r in recent if r.get("success", False))
        recent_sr = recent_successes / len(recent)

        # Latency trend
        latencies = [r.get("latency_ms", 0) for r in records if r.get("latency_ms", 0) > 0]
        recent_latencies = [r.get("latency_ms", 0) for r in recent if r.get("latency_ms", 0) > 0]

        # Degrading model: recent success rate significantly lower
        if recent_sr < 0.7 and recent_sr < success_rate - 0.1:
            patterns.append({
                "type": "degrading_model",
                "target": model,
                "severity": "warning",
                "confidence": round(min(1.0, (success_rate - recent_sr) * 3), 2),
                "evidence": f"{model}: success_rate {recent_sr:.0%} en últimas {len(recent)} requests (global: {success_rate:.0%})",
                "recommendation": f"penalizar peso de {model} en routing o revisar estado",
                "details": {
                    "model": model,
                    "global_success_rate": round(success_rate, 3),
                    "recent_success_rate": round(recent_sr, 3),
                    "total_requests": len(records),
                    "recent_requests": len(recent),
                },
                "timestamp": int(time.time()),
            })
            continue

        # High latency model
        if len(latencies) >= 5 and len(recent_latencies) >= 3:
            avg_lat = sum(latencies) / len(latencies)
            recent_avg = sum(recent_latencies) / len(recent_latencies)
            if recent_avg > 20000 and recent_avg > avg_lat * 1.15:
                patterns.append({
                    "type": "high_latency_model",
                    "target": model,
                    "severity": "warning",
                    "confidence": round(min(1.0, recent_avg / 50000), 2),
                    "evidence": f"{model}: latencia reciente {recent_avg:.0f}ms (global: {avg_lat:.0f}ms, +{(recent_avg/avg_lat-1)*100:.0f}%)",
                    "recommendation": "revisar carga del nodo o reducir max_tokens",
                    "details": {
                        "model": model,
                        "global_avg_latency_ms": round(avg_lat, 1),
                        "recent_avg_latency_ms": round(recent_avg, 1),
                        "drift_pct": round((recent_avg / avg_lat - 1) * 100, 1),
                        "samples": len(latencies),
                    },
                    "timestamp": int(time.time()),
                })

    return patterns


def _detect_recall_quality_patterns(
    incidents: list[dict],
    routing: list[dict],
    cognitive: list[dict],
) -> list[dict]:
    """Detect patterns in recall quality using contamination/noise signals."""
    patterns = []
    _ = routing  # reserved for future semantic queries

    # Cognitive recall quality signals
    if cognitive:
        low_quality = [c for c in cognitive if c.get("quality_score", 1.0) < 0.5]
        if len(low_quality) >= 3:
            patterns.append({
                "type": "recurring_low_recall_quality",
                "target": "cognitive_history",
                "severity": "info",
                "confidence": round(min(1.0, len(low_quality) / max(len(cognitive), 1) * 3), 2),
                "evidence": f"{len(low_quality)}/{len(cognitive)} cognitive snapshots con quality_score < 0.5",
                "recommendation": "revisar umbrales de recall o fuentes de datos",
                "details": {
                    "low_quality_count": len(low_quality),
                    "total": len(cognitive),
                },
                "timestamp": int(time.time()),
            })

    # Incident noise signals (contamination from low-severity)
    if incidents:
        sevs = Counter(p.get("payload", {}).get("severity", "info") for p in incidents)
        total = sum(sevs.values())
        info_pct = sevs.get("info", 0) / total * 100 if total else 0
        if info_pct > 50 and total >= 5:
            patterns.append({
                "type": "noisy_incidents",
                "target": "incidents",
                "severity": "info",
                "confidence": round(min(1.0, info_pct / 80), 2),
                "evidence": f"{info_pct:.0f}% de incidents son info ({sevs.get('info', 0)}/{total})",
                "recommendation": "revisar umbrales de creación de incidents o limpiar ruido",
                "details": {"info_pct": round(info_pct, 1), "by_severity": dict(sevs)},
                "timestamp": int(time.time()),
            })

    return patterns


def latency_trends(days: int = 7) -> list[dict]:
    """Detect latency degradation trends per model from routing history.

    Compares average latency in recent window vs baseline.
    """
    try:
        from runtime.memory.qdrant_store import scroll_all
    except ImportError:
        return []

    cutoff = time.time() - days * 86400
    routing = scroll_all("routing_history")
    routing = [p for p in routing if p["payload"].get("timestamp", 0) >= cutoff]

    if not routing:
        return []

    model_stats: dict[str, list[float]] = defaultdict(list)
    for p in routing:
        p2 = p.get("payload", {})
        model = p2.get("model", "unknown")
        latency = p2.get("latency_ms", 0)
        if latency and latency > 0 and latency < 300000:
            model_stats[model].append(latency)

    trends = []
    for model, latencies in model_stats.items():
        if len(latencies) < 3:
            continue
        avg = sum(latencies) / len(latencies)
        recent = latencies[-max(3, len(latencies) // 3):]
        recent_avg = sum(recent) / len(recent)

        drift_pct = ((recent_avg - avg) / avg * 100) if avg > 0 else 0
        if abs(drift_pct) < 10:
            continue

        trends.append({
            "model": model,
            "samples": len(latencies),
            "overall_avg_ms": round(avg, 1),
            "recent_avg_ms": round(recent_avg, 1),
            "drift_pct": round(drift_pct, 1),
            "direction": "degrading" if drift_pct > 0 else "improving",
        })

    trends.sort(key=lambda t: -abs(t["drift_pct"]))
    return trends
