from __future__ import annotations

import os
import time
from typing import Any

from runtime.tools.contracts import (
    ToolContract,
    ToolAuthorityContract,
    ToolExecutionContract,
    ToolLifecycleContract,
    ToolSafetyContract,
    ToolArtifactContract,
    ToolGovernanceContract,
    TOOL_CONTRACT_VERSION,
)


_CONF = {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.0}


def _strict_mode() -> bool:
    return os.environ.get("STRICT_VALIDATION_MODE", "false").lower() in ("true", "1", "yes")


def build_tool_contracts() -> list[dict[str, Any]]:
    """Formal tool contracts for execution governance.

    Conservative: unknown tools are not considered safe_to_execute.
    """

    tools: list[ToolContract] = []

    # Prometheus tools (operational authority)
    tools.append(ToolContract(
        tool_id="prometheus_targets_audit",
        tool_type="prometheus",
        authority=ToolAuthorityContract(
            authority="operational",
            authority_domain="prometheus",
            source_of_truth="prometheus",
            confidence="high",
        ),
        execution=ToolExecutionContract(
            tool_id="prometheus_targets_audit",
            tool_type="prometheus",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=10,
            produces_artifacts=False,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(
            safe_to_execute=True,
            deterministic=True,
            reasons=["read-only audit"],
        ),
        artifacts=[ToolArtifactContract(
            artifact_type="observability_audit",
            paths=["/runtime/observability/*"],
            lifecycle="active",
            protected=True,
        )],
        artifact_policy="protected_authority",
        deterministic=True,
    ))

    # Validation tools (execution authority)
    tools.append(ToolContract(
        tool_id="runtime_validation_33b",
        tool_type="validation",
        authority=ToolAuthorityContract(
            authority="execution",
            authority_domain="validation",
            source_of_truth="runtime/validation",
            confidence="high",
        ),
        execution=ToolExecutionContract(
            tool_id="runtime_validation_33b",
            tool_type="validation",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=10,
            produces_artifacts=True,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(
            safe_to_execute=True,
            deterministic=True,
            safe_to_delete=False,
            reasons=["validation only"],
        ),
        artifacts=[ToolArtifactContract(
            artifact_type="validation_report",
            paths=["/tmp/33b-*.json", "/tmp/33b-summary.md"],
            lifecycle="historical",
            protected=True,
            retention_days=14,
        )],
        artifact_policy="protected_validation",
        deterministic=True,
    ))

    # Reporting tools (derived authority)
    tools.append(ToolContract(
        tool_id="operational_reporting_31c",
        tool_type="reporting",
        authority=ToolAuthorityContract(
            authority="derived",
            authority_domain="reporting",
            source_of_truth="runtime/reporting",
            confidence="medium",
        ),
        execution=ToolExecutionContract(
            tool_id="operational_reporting_31c",
            tool_type="reporting",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=10,
            produces_artifacts=False,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(safe_to_execute=True, deterministic=True, reasons=["derived report"]),
        artifacts=[],
        artifact_policy="none",
        deterministic=True,
    ))

    # GC tools (restricted authority): never execute destructive actions
    tools.append(ToolContract(
        tool_id="crossplan_gc_28_4",
        tool_type="gc",
        authority=ToolAuthorityContract(
            authority="restricted",
            authority_domain="gc",
            source_of_truth="runtime/gc",
            confidence="high",
        ),
        execution=ToolExecutionContract(
            tool_id="crossplan_gc_28_4",
            tool_type="gc",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=10,
            produces_artifacts=True,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(
            safe_to_execute=True,
            safe_to_delete=False,
            safe_to_archive=False,
            safe_to_rotate=False,
            safe_to_expire=False,
            deterministic=True,
            reasons=["dry-run only; no destructive execution"],
        ),
        artifacts=[ToolArtifactContract(
            artifact_type="gc_inventory",
            paths=["/tmp/28_4-gc-*.json"],
            lifecycle="historical",
            protected=True,
            retention_days=14,
        )],
        artifact_policy="protected_gc_plan",
        deterministic=True,
    ))

    # Inventory shell tool (informational authority only)
    tools.append(ToolContract(
        tool_id="shell_tool",
        tool_type="shell",
        authority=ToolAuthorityContract(
            authority="informational",
            authority_domain="inventory",
            source_of_truth="runtime/tools/shell_tool.py",
            confidence="medium",
        ),
        execution=ToolExecutionContract(
            tool_id="shell_tool",
            tool_type="shell",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=False,
            max_duration_seconds=30,
            produces_artifacts=False,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(
            safe_to_execute=True,
            deterministic=False,
            reasons=["command allowlist + blocked patterns"],
        ),
        artifacts=[],
        artifact_policy="none",
        deterministic=False,
    ))

    # Agentic readonly executor surface (informational/execution)
    tools.append(ToolContract(
        tool_id="readonly_executor",
        tool_type="executor",
        authority=ToolAuthorityContract(
            authority="execution",
            authority_domain="agentic",
            source_of_truth="runtime/agentic/readonly_executor.py",
            confidence="high",
        ),
        execution=ToolExecutionContract(
            tool_id="readonly_executor",
            tool_type="executor",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=60,
            produces_artifacts=True,
        ),
        lifecycle=ToolLifecycleContract(execution_state="enabled", lifecycle="active"),
        safety=ToolSafetyContract(
            safe_to_execute=True,
            safe_to_delete=False,
            deterministic=True,
            reasons=["readonly command registry"],
        ),
        artifacts=[ToolArtifactContract(
            artifact_type="execution_audit",
            paths=["/opt/ai-lab/runtime/state/*.jsonl"],
            lifecycle="active",
            protected=True,
        )],
        artifact_policy="protected_audit",
        deterministic=True,
    ))

    # Sandbox write executor exists but is gated by environment
    sandbox_enabled = os.environ.get("AI_LAB_ENABLE_SANDBOX_WRITE", "false").lower() in ("true", "1", "yes")
    tools.append(ToolContract(
        tool_id="sandbox_write_executor",
        tool_type="executor",
        authority=ToolAuthorityContract(
            authority="restricted",
            authority_domain="agentic",
            source_of_truth="runtime/agentic/sandbox_executor.py",
            confidence="medium" if sandbox_enabled else "high",
        ),
        execution=ToolExecutionContract(
            tool_id="sandbox_write_executor",
            tool_type="executor",
            contract_version=TOOL_CONTRACT_VERSION,
            deterministic=True,
            max_duration_seconds=120,
            produces_artifacts=True,
        ),
        lifecycle=ToolLifecycleContract(
            execution_state="enabled" if sandbox_enabled else "disabled",
            lifecycle="active",
        ),
        safety=ToolSafetyContract(
            safe_to_execute=bool(sandbox_enabled),
            deterministic=True,
            reasons=["sandbox gated by env flag"],
        ),
        artifacts=[ToolArtifactContract(
            artifact_type="sandbox_artifacts",
            paths=["/opt/ai-lab/runtime/state/sandbox_artifacts.jsonl"],
            lifecycle="active",
            protected=True,
            retention_days=30,
        )],
        artifact_policy="protected_sandbox",
        deterministic=True,
    ))

    return [t.to_dict() for t in tools]


def build_tool_registry() -> dict[str, Any]:
    contracts = build_tool_contracts()
    return {
        "contract_version": TOOL_CONTRACT_VERSION,
        "generated_at": 0.0 if _strict_mode() else time.time(),
        "tools": contracts,
        "total_tools": len(contracts),
    }


def build_tool_authority_map() -> dict[str, Any]:
    contracts = build_tool_contracts()
    m = {}
    for t in contracts:
        m[t["tool_id"]] = {
            "authority": (t.get("authority") or {}).get("authority"),
            "authority_domain": (t.get("authority") or {}).get("authority_domain"),
            "source_of_truth": (t.get("authority") or {}).get("source_of_truth"),
            "confidence": (t.get("authority") or {}).get("confidence"),
        }
    return {
        "contract_version": TOOL_CONTRACT_VERSION,
        "authority_map": m,
        "total": len(m),
    }


def build_tool_execution_surface() -> dict[str, Any]:
    contracts = build_tool_contracts()
    safe = [t["tool_id"] for t in contracts if (t.get("safety") or {}).get("safe_to_execute")]
    deterministic = [t["tool_id"] for t in contracts if t.get("deterministic")]
    return {
        "contract_version": TOOL_CONTRACT_VERSION,
        "safe_to_execute": safe,
        "deterministic_tools": deterministic,
        "strict_mode": _strict_mode(),
    }


def build_tool_lifecycle_summary() -> dict[str, Any]:
    contracts = build_tool_contracts()
    by_state: dict[str, int] = {}
    for t in contracts:
        state = (t.get("lifecycle") or {}).get("execution_state", "unknown")
        by_state[state] = by_state.get(state, 0) + 1
    return {
        "contract_version": TOOL_CONTRACT_VERSION,
        "execution_state_counts": by_state,
    }


def detect_invalid_tool_contracts() -> list[dict[str, Any]]:
    invalid = []
    for t in build_tool_contracts():
        if not t.get("tool_id") or not t.get("tool_type"):
            invalid.append({"tool_id": t.get("tool_id"), "reason": "missing id/type"})
        if (t.get("authority") or {}).get("authority") in (None, ""):
            invalid.append({"tool_id": t.get("tool_id"), "reason": "missing authority"})
        if (t.get("execution") or {}).get("contract_version") != TOOL_CONTRACT_VERSION:
            invalid.append({"tool_id": t.get("tool_id"), "reason": "contract_version mismatch"})
    return invalid


def detect_orphan_tools() -> list[str]:
    # Orphan = tool exists but no known plan references it.
    try:
        from runtime.plans.plan_registry import build_plan_dependencies
        deps = build_plan_dependencies()
        referenced = set(deps.get("tools", []))
    except Exception:
        referenced = set()
    all_tools = {t["tool_id"] for t in build_tool_contracts()}
    return sorted([t for t in all_tools if t not in referenced])


def calculate_tool_governance_score() -> dict[str, Any]:
    invalid = detect_invalid_tool_contracts()
    orphan = detect_orphan_tools()

    base = 1.0
    base -= min(0.5, len(invalid) * 0.1)
    base -= min(0.3, len(orphan) * 0.03)
    score = round(max(0.0, min(1.0, base)) * 100, 1)

    issues = []
    if invalid:
        issues.append(f"invalid_tool_contracts={len(invalid)}")
    if orphan:
        issues.append(f"orphan_tools={len(orphan)}")

    gov = ToolGovernanceContract(
        tool_governance_score=score,
        invalid_tool_contracts_total=len(invalid),
        orphan_tools_total=len(orphan),
        deterministic=True,
        explainable=True,
        issues=issues,
    )
    return gov.to_dict()
