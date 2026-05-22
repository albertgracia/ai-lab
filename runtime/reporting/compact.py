from __future__ import annotations

from typing import Any


def format_compact_report(contract: Any) -> str:
    d = contract.to_dict() if hasattr(contract, "to_dict") else contract

    lines = [
        "AI-LAB Runtime",
        f"topology={d.get('topology_mode', 'unknown')}",
        f"runtime_state={d.get('runtime_state', 'unknown')}",
        f"confidence={d.get('confidence', 'unknown')}",
        f"maturity_score={d.get('maturity_score', 0.0)}",
        f"operational_impact={d.get('operational_impact', 'none')}",
        f"uncertainty={d.get('uncertainty_level', 'unknown')}",
        f"freshness={d.get('freshness', 'unknown')}",
    ]

    degraded = d.get("degraded_domains", []) or []
    if degraded:
        lines.append(f"degraded_domains={','.join(degraded)}")

    unknown = d.get("unknown_domains", []) or []
    if unknown:
        lines.append(f"unknown_domains={','.join(unknown)}")

    reasons = d.get("degradation_reason", []) or []
    if reasons:
        lines.append(f"degradation_reason={' | '.join(reasons[:3])}")

    return "\n".join(lines)
