"""AI-LAB Validation Authority — read-only action validation layer.

Evaluates proposed actions against operator intent, observability triage,
evidence availability, rollback requirements, and governance policy.

NO auto-execution. NO mutations. Read-only decision engine.
"""

import os
import re
import time
from typing import Any

VALIDATION_AUTHORITY_CONTRACT_VERSION = "VALIDATION-AUTHORITY-01"

SAFE_TO_AUTO_EXECUTE = False  # hardcoded false in this phase


# ── Risk patterns (aligned with operator_intent_reasoning.py) ──────

_DESTRUCTIVE_TERMS = (
    "rm -rf", "shutdown", "reboot", "format", "drop database",
    "delete all", "truncate", "reset --hard",
)
_RESTART_TERMS = ("restart", "reinicia", "systemctl restart", "service restart", "reboot")
_DEPLOY_TERMS = ("deploy", "despliega", "release", "rollout", "publish")
_GIT_TERMS = ("git push", "git commit", "git merge", "git rebase", "push to origin", "push --force")
_EXECUTION_TERMS = ("execute", "run", "aplica", "apply", "deploy", "despliega", "push")
_DELETE_TERMS = ("delete", "borra", "borrar", "eliminar", "rm -rf", "drop", "truncate")
_DISABLE_TERMS = ("disable", "deshabilit", "desactiv", "stop", "kill")
_MODIFY_SERVICE_TERMS = ("modify", "change", "edit", "update", "reconfigur")


def _norm(text: str) -> str:
    t = (text or "").lower().strip()
    return re.sub(r"\s+", " ", t)


def _term_in(text: str, terms: tuple[str, ...]) -> bool:
    t = _norm(text)
    for term in terms:
        if term in t:
            return True
    return False


def _matches_pattern(text: str, patterns: list[str]) -> list[str]:
    t = _norm(text)
    matched: list[str] = []
    for pat in patterns:
        if pat in t:
            matched.append(pat)
    return matched


# ── Evidence requirements per action type ──────────────────────────

_EVIDENCE_REQUIREMENTS: dict[str, list[str]] = {
    "gateway-health": ["gateway_health_endpoint"],
    "explain-route": ["routing_history", "operator_intent"],
    "prepare-deploy": ["git_status", "test_results", "triage_status"],
    "rollback-plan": ["previous_snapshot", "change_log"],
    "restart-gateway": ["gateway_health_endpoint", "triage_status", "reason_provided"],
    "push-code": ["git_status_clean", "test_results", "triage_status"],
    "deploy-change": ["git_status_clean", "test_results", "triage_status", "rollback_plan"],
    "delete-logs": ["log_path_confirmation", "backup_available", "operator_consent"],
    "disable-prometheus": ["prometheus_health", "alert_rules_backup", "operator_consent", "emergency_justification"],
    "disable-slo": ["slo_impact_analysis", "operator_consent", "emergency_justification"],
    "reset-hard": ["full_backup", "operator_consent", "emergency_justification"],
    "default": ["operator_intent", "triage_status"],
}


def _action_type(text: str) -> str:
    t = _norm(text)
    if _term_in(t, _DESTRUCTIVE_TERMS) or ("reset" in t and "--hard" in t):
        return "reset-hard"
    if _term_in(t, _DELETE_TERMS) or ("delete" in t and ("log" in t or "file" in t)):
        return "delete-logs"
    if "prometheus" in t and _term_in(t, _DISABLE_TERMS + ("delete", "stop", "kill", "rm")):
        return "disable-prometheus"
    if "slo" in t and _term_in(t, _DISABLE_TERMS + ("delete",)):
        return "disable-slo"
    if "prepare" in t and "deploy" in t:
        return "prepare-deploy"
    if "rollback" in t or "recover" in t:
        return "rollback-plan"
    if _term_in(t, _RESTART_TERMS):
        return "restart-gateway"
    if _term_in(t, _DEPLOY_TERMS):
        return "deploy-change"
    if _term_in(t, _GIT_TERMS):
        if "push" in t:
            return "push-code"
        return "deploy-change"
    if _term_in(t, _EXECUTION_TERMS):
        return "deploy-change"
    if "gateway" in t and _term_in(t, ("health", "status", "show")):
        return "gateway-health"
    if "explain" in t or ("last" in t and "route" in t):
        return "explain-route"
    return "default"


def _classify_risk(action_type: str) -> str:
    high_risk = {"restart-gateway", "deploy-change", "push-code", "prepare-deploy"}
    critical_risk = {"reset-hard", "delete-logs", "disable-prometheus", "disable-slo"}
    if action_type in critical_risk:
        return "critical"
    if action_type in high_risk:
        return "high"
    if action_type in ("rollback-plan",):
        return "medium"
    return "low"


def _classify_severity(action_type: str) -> str:
    critical = {"reset-hard", "disable-prometheus", "disable-slo"}
    high = {"restart-gateway", "deploy-change", "push-code", "delete-logs"}
    if action_type in critical:
        return "critical"
    if action_type in high:
        return "high"
    if action_type in ("prepare-deploy", "rollback-plan"):
        return "medium"
    return "info"


def _affected_components(action_type: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "gateway-health": ["gateway"],
        "explain-route": ["gateway", "router"],
        "prepare-deploy": ["gateway", "codebase"],
        "rollback-plan": ["runtime_state", "codebase"],
        "restart-gateway": ["gateway"],
        "push-code": ["codebase", "git"],
        "deploy-change": ["codebase", "gateway", "services"],
        "delete-logs": ["filesystem", "storage"],
        "disable-prometheus": ["observability", "prometheus"],
        "disable-slo": ["governance", "slo"],
        "reset-hard": ["codebase", "filesystem", "git"],
    }
    return mapping.get(action_type, ["unknown"])


# ── Evidence assessment ───────────────────────────────────────────

_READ_ONLY_TYPES = {"gateway-health", "explain-route"}
_DESTRUCTIVE_TYPES = {"reset-hard", "delete-logs", "disable-prometheus", "disable-slo"}
_HIGH_IMPACT_TYPES = {"restart-gateway", "deploy-change", "push-code", "prepare-deploy"}


def assess_evidence(
    action_type: str,
    operator_intent: dict[str, Any] | None,
    triage: dict[str, Any] | None,
    context: dict[str, Any] | None,
) -> tuple[list[str], list[str]]:
    """Return (evidence_found, evidence_missing)."""
    required = _EVIDENCE_REQUIREMENTS.get(action_type, _EVIDENCE_REQUIREMENTS["default"])
    found: list[str] = []
    missing: list[str] = []

    for req in required:
        if req == "operator_intent":
            if operator_intent and operator_intent.get("category"):
                found.append("operator_intent")
            else:
                missing.append("operator_intent")
        elif req == "triage_status":
            if triage and triage.get("triage_id"):
                found.append("triage_status")
            else:
                missing.append("triage_status")
        elif req == "gateway_health_endpoint":
            found.append("gateway_health_endpoint")
        elif req == "reason_provided":
            if operator_intent and operator_intent.get("category"):
                found.append("reason_provided")
            else:
                missing.append("reason_provided")
        elif req == "git_status":
            if context and context.get("git_status"):
                found.append("git_status")
            else:
                missing.append("git_status")
        elif req == "git_status_clean":
            if context and context.get("git_status") == "clean":
                found.append("git_status_clean")
            else:
                missing.append("git_status_clean")
        elif req == "test_results":
            if context and context.get("tests_passing") is True:
                found.append("test_results")
            else:
                missing.append("test_results")
        elif req == "rollback_plan":
            if context and context.get("rollback_plan"):
                found.append("rollback_plan")
            else:
                missing.append("rollback_plan")
        elif req == "previous_snapshot":
            if context and context.get("snapshot_available"):
                found.append("previous_snapshot")
            else:
                missing.append("previous_snapshot")
        elif req == "change_log":
            if context and context.get("change_log"):
                found.append("change_log")
            else:
                missing.append("change_log")
        elif req == "backup_available":
            if context and context.get("backup_available") is True:
                found.append("backup_available")
            else:
                missing.append("backup_available")
        elif req == "full_backup":
            if context and context.get("full_backup") is True:
                found.append("full_backup")
            else:
                missing.append("full_backup")
        elif req == "operator_consent":
            if operator_intent and operator_intent.get("requires_approval") is False:
                found.append("operator_consent")
            else:
                missing.append("operator_consent")
        elif req == "log_path_confirmation":
            if context and context.get("log_path_confirmed"):
                found.append("log_path_confirmation")
            else:
                missing.append("log_path_confirmation")
        elif req == "emergency_justification":
            if context and context.get("emergency_justification"):
                found.append("emergency_justification")
            else:
                missing.append("emergency_justification")
        elif req == "prometheus_health":
            found.append("prometheus_health")
        elif req == "alert_rules_backup":
            if context and context.get("alert_rules_backup"):
                found.append("alert_rules_backup")
            else:
                missing.append("alert_rules_backup")
        elif req == "slo_impact_analysis":
            if context and context.get("slo_impact_analysis"):
                found.append("slo_impact_analysis")
            else:
                missing.append("slo_impact_analysis")
        else:
            found.append(req)

    return found, missing


def assess_rollback(
    action_type: str,
    context: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    """Return (has_rollback, rollback_steps)."""
    if action_type in _READ_ONLY_TYPES:
        return True, ["no rollback needed — read-only action"]

    has_rollback = False
    steps: list[str] = []

    if context and context.get("rollback_plan"):
        has_rollback = True
        plan = context["rollback_plan"]
        if isinstance(plan, list):
            steps = plan
        elif isinstance(plan, str):
            steps = [plan]

    if action_type == "restart-gateway":
        if not has_rollback:
            steps = [
                "systemctl restart ailab-gateway",
                "verify with curl http://192.168.1.30:8008/health",
                "if fail: restore from previous state snapshot",
            ]
        return True, steps

    if action_type in _DESTRUCTIVE_TYPES and not has_rollback:
        return False, ["no rollback plan available for destructive action"]

    if action_type in _HIGH_IMPACT_TYPES and not has_rollback:
        steps = [
            "git revert or restore from backup",
            "systemctl restart affected services",
            "verify health endpoints",
        ]
        return False, steps

    return has_rollback, steps


def assess_approval_requirement(
    action_type: str,
    risk: str,
    operator_intent: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Return (requires_approval, approval_level)."""
    if action_type in _DESTRUCTIVE_TYPES:
        return True, "emergency"

    if risk == "critical":
        return True, "emergency"

    if action_type in {"restart-gateway", "deploy-change", "push-code"}:
        return True, "admin"

    if risk == "high":
        return True, "admin"

    if operator_intent and operator_intent.get("requires_approval"):
        return True, "operator"

    if action_type in {"prepare-deploy", "rollback-plan"}:
        return True, "operator"

    return False, "none"


def build_validation_decision(
    requested_action: str,
    operator_intent: dict[str, Any] | None = None,
    triage: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    now: float | None = None,
) -> dict[str, Any]:
    """Build a complete validation authority decision.

    Evaluates a proposed action against operator intent, observability triage,
    evidence availability, rollback requirements, and governance policy.
    """
    ts = now if now is not None else time.time()
    action_type = _action_type(requested_action)
    risk = _classify_risk(action_type)
    severity = _classify_severity(action_type)
    affected = _affected_components(action_type)

    evidence_found, evidence_missing = assess_evidence(
        action_type, operator_intent, triage, context
    )
    has_rollback, rollback_steps = assess_rollback(action_type, context)
    requires_approval, approval_level = assess_approval_requirement(
        action_type, risk, operator_intent
    )

    # ── Decision logic ────────────────────────────────────────────
    decision: str
    reason_parts: list[str] = []
    next_steps: list[str] = []

    if action_type in _DESTRUCTIVE_TYPES:
        if len(evidence_found) <= 1:
            decision = "block"
            reason_parts.append("destructive action requires sufficient evidence")
            next_steps = ["provide evidence", "justify destructive action"]
        elif len(evidence_found) < len(evidence_missing):
            decision = "require_more_evidence"
            reason_parts.append(f"destructive action missing critical evidence: {evidence_missing}")
            next_steps = [f"provide: {e}" for e in evidence_missing[:5]]
        else:
            decision = "require_approval"
            reason_parts.append("destructive action — emergency approval required")
            next_steps = [
                "provide emergency justification",
                "confirm backup availability",
                "obtain emergency approval from admin",
            ]

    elif risk == "critical":
        if evidence_missing:
            decision = "block"
            reason_parts.append(f"critical risk action missing evidence: {evidence_missing}")
        else:
            decision = "require_approval"
            reason_parts.append("critical risk action requires emergency approval")
        next_steps = ["provide complete evidence", "obtain emergency approval"]

    elif risk == "high":
        if evidence_missing:
            decision = "require_more_evidence"
            reason_parts.append(f"high risk action missing evidence: {evidence_missing}")
            next_steps = [f"provide missing evidence: {e}" for e in evidence_missing[:5]]
        elif not has_rollback and action_type in _HIGH_IMPACT_TYPES:
            decision = "require_more_evidence"
            reason_parts.append("high impact action requires rollback plan")
            next_steps = ["provide rollback plan", "test rollback procedure"]
        else:
            decision = "require_approval"
            reason_parts.append("high risk action requires admin approval")
            next_steps = ["submit for admin approval", "ensure rollback plan is ready"]

    elif risk == "medium":
        if action_type == "rollback-plan":
            decision = "require_approval"
            reason_parts.append("rollback plan requires operator approval")
            next_steps = ["submit for operator approval"]
            if evidence_missing:
                next_steps = [f"provide optional evidence: {e}" for e in evidence_missing[:3]]
        elif evidence_missing:
            decision = "require_more_evidence"
            reason_parts.append(f"medium risk action missing evidence: {evidence_missing}")
            next_steps = [f"provide missing evidence: {e}" for e in evidence_missing[:3]]
        else:
            decision = "require_approval"
            reason_parts.append("medium risk action requires operator approval")
            next_steps = ["submit for operator approval"]

    else:  # low risk / read-only
        if action_type in _READ_ONLY_TYPES:
            decision = "allow"
            reason_parts.append("read-only action — no approval needed")
            next_steps = ["execute read-only action"]
        elif action_type == "default":
            decision = "allow"
            reason_parts.append("unknown action type classified as low risk")
            next_steps = ["clarify intent if action seems wrong"]
        else:
            if evidence_missing:
                decision = "require_more_evidence"
                reason_parts.append(f"missing evidence: {evidence_missing}")
                next_steps = [f"provide: {e}" for e in evidence_missing[:3]]
            else:
                decision = "allow"
                reason_parts.append("low risk action — sufficient evidence")
                next_steps = ["execute action"]

    # ── Triage integration ────────────────────────────────────────
    if triage and triage.get("severity") in ("critical", "high"):
        if decision == "allow":
            decision = "require_approval"
            reason_parts.insert(
                0, f"triage severity is {triage['severity']} — requires precaution"
            )
            next_steps.insert(0, "review triage findings before proceeding")
        elif decision == "require_approval":
            reason_parts.insert(
                0, f"triage severity elevated ({triage['severity']})"
            )

    if triage and triage.get("severity") == "critical" and risk in ("high", "critical"):
        if decision != "block":
            decision = "block"
            reason_parts.insert(0, "CRITICAL triage status blocks risky actions")

    # ── Evidence confidence ───────────────────────────────────────
    total_required = len(_EVIDENCE_REQUIREMENTS.get(action_type, _EVIDENCE_REQUIREMENTS["default"]))
    evidence_ratio = len(evidence_found) / max(total_required, 1)
    confidence = round(min(1.0, evidence_ratio * 0.7 + 0.3), 3)

    # ── Operator intent safety override ───────────────────────────
    if operator_intent:
        oi_safety = operator_intent.get("safety", {})
        oi_unsafe = oi_safety.get("unsafe_action_markers", [])
        if oi_unsafe and decision not in ("block", "require_approval"):
            decision = "require_approval"
            reason_parts.append(f"operator intent flagged unsafe markers: {oi_unsafe}")

    preconditions: list[str] = []
    if action_type not in _READ_ONLY_TYPES:
        preconditions.append("working tree must be clean (for code changes)")
        preconditions.append("tests must pass before deployment")
        preconditions.append("rollback plan must be available")
    if action_type in _DESTRUCTIVE_TYPES:
        preconditions.append("full backup must exist")
        preconditions.append("emergency contact must be notified")

    validation_id = f"VA-{int(ts)}-{action_type}"

    return {
        "validation_id": validation_id,
        "timestamp": ts,
        "requested_action": requested_action,
        "action_type": action_type,
        "operator_intent": {
            "category": operator_intent.get("category") if operator_intent else None,
            "risk": operator_intent.get("risk") if operator_intent else None,
            "requires_approval": operator_intent.get("requires_approval") if operator_intent else None,
            "recommended_action": operator_intent.get("recommended_action") if operator_intent else None,
        } if operator_intent else None,
        "risk": risk,
        "severity": severity,
        "evidence": evidence_found,
        "missing_evidence": evidence_missing,
        "preconditions": preconditions,
        "validation_plan": [
            "check evidence completeness",
            "verify operator intent classification",
            "evaluate triage status",
            "assess rollback availability",
            "determine approval level",
        ],
        "rollback_plan": rollback_steps if has_rollback else [],
        "has_rollback": has_rollback,
        "expected_impact": f"{severity.upper()} risk action affecting {len(affected)} component(s): {', '.join(affected)}",
        "affected_components": affected,
        "requires_approval": requires_approval,
        "approval_level": approval_level,
        "safe_to_execute": decision == "allow",
        "safe_to_auto_execute": SAFE_TO_AUTO_EXECUTE,
        "decision": decision,
        "reason": "; ".join(reason_parts),
        "confidence": confidence,
        "next_steps": next_steps,
        "contract_version": VALIDATION_AUTHORITY_CONTRACT_VERSION,
    }


def validate_action_request(
    text: str,
    *,
    operator_intent: dict[str, Any] | None = None,
    triage: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience wrapper for quick validation."""
    return build_validation_decision(
        requested_action=text,
        operator_intent=operator_intent,
        triage=triage,
        context=context,
    )
