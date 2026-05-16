"""Runtime Pattern Learning — detect operational patterns from Qdrant data.

Reads incidents, routing_history, and cognitive_history to identify:
  - Node failure patterns (frequency, recurrence, severity trends)
  - Latency degradation (per-model, per-node trends)
  - Context overflow patterns (budget spikes, timing)
  - Time-based clustering (failure windows, peak issue hours)
  - Model performance degradation (success rate + latency drift)

Usage:
    from runtime.memory.pattern_learner import learn_patterns
    patterns = learn_patterns(days=7)
"""

import time
from collections import Counter, defaultdict


def learn_patterns(days: int = 7) -> list[dict]:
    """Run all pattern detectors and return ranked patterns.

    Each pattern is a dict:
        type: str          — pattern category
        label: str         — human-readable summary
        severity: str      — critical/warning/info
        confidence: float  — 0.0 to 1.0
        details: dict      — supporting data
        timestamp: int     — when detected
    """
    patterns = []

    try:
        from runtime.memory.qdrant_store import scroll_all
    except ImportError:
        return [{"type": "error", "label": "Qdrant store unavailable", "severity": "critical", "confidence": 1.0, "details": {}, "timestamp": int(time.time())}]

    cutoff = time.time() - days * 86400

    incidents = scroll_all("incidents")
    incidents = [p for p in incidents if p["payload"].get("timestamp", 0) >= cutoff]

    patterns.extend(_detect_node_failure_patterns(incidents))
    patterns.extend(_detect_severity_trends(incidents))
    patterns.extend(_detect_peak_hours(incidents))
    patterns.sort(key=lambda p: (-p["confidence"], p["severity"]))
    return patterns


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
                "label": f"Node {node} failed {count} times",
                "severity": sev,
                "confidence": round(confidence, 2),
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
            "label": f"{critical_pct:.0f}% of incidents are critical ({severities['critical']}/{total})",
            "severity": "critical",
            "confidence": round(min(1.0, critical_pct / 50), 2),
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
            "label": f"Peak failures at UTC hour {peak_hour}:00 ({peak_count}/{total}, {peak_pct:.0f}%)",
            "severity": "warning",
            "confidence": round(min(1.0, peak_pct / 40), 2),
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
