from __future__ import annotations

from typing import Any


def format_operational_metric_line(key: str, value: Any, unit: str = "") -> str:
    if value is None or value == "":
        return f"{key}=NO DISPONIBLE"
    return f"{key}={value}{unit}"


def _thermal_state(temp_c: float | int | None) -> str:
    if temp_c is None:
        return "unknown"
    if float(temp_c) < 70:
        return "stable"
    if float(temp_c) < 85:
        return "warm"
    return "hot"


def _source_string(summary: dict[str, Any]) -> str:
    sources = summary.get("source_of_truth", [])
    if not isinstance(sources, list) or not sources:
        return "unknown"
    return "+".join(str(item) for item in sources)


def format_gpu_inventory_state(summary: dict[str, Any]) -> str:
    observed = summary.get("observed_state", "unknown")
    topology_role = summary.get("topology_role", "unknown")
    confidence = summary.get("confidence", "unknown")
    freshness = summary.get("freshness", {}) if isinstance(summary.get("freshness"), dict) else {}
    freshness_status = freshness.get("status", "unavailable")
    lines = [
        str(summary.get("gpu_id", summary.get("name", "GPU"))),
        f"status={summary.get('operational_state', 'inactive')}",
        f"observed_state={observed}",
        f"topology_role={topology_role}",
        f"freshness={freshness_status}",
        f"confidence={confidence}",
        f"source={_source_string(summary)}",
    ]
    return "\n".join(lines)


def format_gpu_operational_summary(summary: dict[str, Any]) -> str:
    metrics = summary.get("observed_metrics", {}) if isinstance(summary.get("observed_metrics"), dict) else {}
    freshness = summary.get("freshness", {}) if isinstance(summary.get("freshness"), dict) else {}
    freshness_status = freshness.get("status", "unavailable")
    freshness_age = freshness.get("age_seconds")
    freshness_str = freshness_status if freshness_age is None else f"{freshness_status}({int(round(float(freshness_age)))}s)"
    vram_used = metrics.get("vram_used_gb")
    vram_total = metrics.get("vram_total_gb")
    vram_line = "vram=NO DISPONIBLE"
    if vram_used is not None and vram_total is not None:
        vram_line = f"vram={vram_used}/{round(float(vram_total), 1)}GB"

    lines = [
        str(summary.get("gpu_id", summary.get("name", "GPU"))),
        f"status={summary.get('operational_state', summary.get('status', 'unknown'))}",
        f"topology_role={summary.get('topology_role', 'unknown')}",
        f"thermal={_thermal_state(metrics.get('temperature_c'))}",
        format_operational_metric_line("gpu_load", metrics.get("gpu_load_percent"), "%"),
        format_operational_metric_line("power", metrics.get("power_watts"), "W"),
        vram_line,
        f"freshness={freshness_str}",
        f"confidence={summary.get('confidence', 'unknown')}",
        f"source={_source_string(summary)}",
    ]
    if metrics.get("fan_rpm") is not None:
        lines.insert(6, format_operational_metric_line("fan", metrics.get("fan_rpm"), "RPM"))
    return "\n".join(lines)


def format_gpu_operational_block(
    summaries: list[dict[str, Any]],
    *,
    target_gpu: str | None = None,
    mode: str = "operational_compact",
) -> str:
    if not summaries:
        return "GPU\nstatus=NO DISPONIBLE\nfreshness=unavailable\nconfidence=low\nsource=unknown"
    selected = summaries
    if target_gpu:
        needle = target_gpu.lower()
        selected = [item for item in summaries if str(item.get("gpu_id", "")).lower() == needle]
        if not selected:
            selected = summaries
    blocks: list[str] = []
    for summary in selected:
        if summary.get("observed_state") == "expected_offline":
            blocks.append(format_gpu_inventory_state(summary))
        else:
            blocks.append(format_gpu_operational_summary(summary))
    return "\n\n".join(blocks)
