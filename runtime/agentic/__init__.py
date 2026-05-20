"""FASE 28.3 — Agentic Runtime (Readonly + Sandbox Write).

This package implements the agentic runtime pipeline:
  1. Action Intent Layer (intents, not tool_calls)
  2. Workflow Planner (intents → DAG)
  3. Deterministic Risk Engine (rules, never LLM)
  4. Dry-Run Engine (simulation without execution)
  5. Human Explainability Layer (natural language summaries)
  6. Approval Gate (HMAC tickets, TTL, single-use)
  7. Simulation Executor (NO-OP when AGENTIC_EXECUTION_ENABLED=false)
  8. Readonly Executor (safe subprocess with shell=False, command validation)
  9. Sandbox Write Executor (Python I/O, governance, rollback)
  10. Safe Runner (command sanitization + execution policies)
  11. Verifier (workflow consistency checks)
  12. Workflow State Machine (incl. MUTATING, ROLLED_BACK)
  13. Replay & Audit Extension
  14. Simulation-Only Guards (prevents ANY real execution)
  15. Readonly Policies (governance + risk + scope pre-validation)
  16. Execution Audit (JSONL trail with hashes)
  17. Sandbox Policies (write governance, chmod prohibition)
  18. Sandbox Filesystem (boundary enforcement, path depth)
  19. Sandbox Audit (mutation_class, checksums before/after)
  20. Artifact Registry (lineage DAG, workflow budget)
  21. Rollback Engine (snapshot SHA-256, post-restore validation)
  22. Mutation Context (MutationClass, budget counters)

CRITICAL: FASE 28.3 enables workspace_write_reserved scope for sandbox.
All writes use Python I/O only — NO subprocess, NO chmod.
"""

from runtime.agentic.workflow_state import WorkflowState, AgenticEvent
from runtime.agentic.intents import KNOWN_INTENTS, IntentParser
from runtime.agentic.sandbox_fs import (
    SANDBOX_ROOTS, MAX_PATH_DEPTH,
    resolve_sandbox_path, is_within_sandbox, ensure_sandbox_dir,
    detect_symlink_escape, detect_path_traversal, check_path_depth,
)
from runtime.agentic.sandbox_registry import (
    SANDBOX_OPERATIONS, SANDBOX_WRITE_INTENTS,
    MutationClass, RiskLevel,
    is_allowed_operation, op_for_intent,
)
from runtime.agentic.sandbox_policies import (
    check_sandbox_governance, assess_sandbox_risk,
    detect_chmod_intent,
)
from runtime.agentic.sandbox_audit import (
    SandboxAuditEntry, write_sandbox_audit,
    read_sandbox_audit, get_sandbox_audit_stats,
)
from runtime.agentic.artifact_registry import (
    ArtifactEntry, ArtifactRegistry,
)
from runtime.agentic.rollback_engine import (
    RollbackSnapshot, RollbackResult,
    Snapshotter, RollbackEngine,
)
from runtime.agentic.mutation_context import (
    MutationExecutionContext,
)
from runtime.agentic.sandbox_executor import (
    SandboxWriteExecutor,
    ENABLE_SANDBOX_WRITE, DRY_RUN,
)

__all__ = [
    "WorkflowState",
    "AgenticEvent",
    "KnownIntents",
    "IntentParser",
    # Sandbox FS
    "SANDBOX_ROOTS", "MAX_PATH_DEPTH",
    "resolve_sandbox_path", "is_within_sandbox", "ensure_sandbox_dir",
    "detect_symlink_escape", "detect_path_traversal", "check_path_depth",
    # Sandbox Registry
    "SANDBOX_OPERATIONS", "SANDBOX_WRITE_INTENTS",
    "MutationClass", "RiskLevel",
    "is_allowed_operation", "op_for_intent",
    # Sandbox Policies
    "check_sandbox_governance", "assess_sandbox_risk",
    "detect_chmod_intent",
    # Sandbox Audit
    "SandboxAuditEntry", "write_sandbox_audit",
    "read_sandbox_audit", "get_sandbox_audit_stats",
    # Artifact Registry
    "ArtifactEntry", "ArtifactRegistry",
    # Rollback Engine
    "RollbackSnapshot", "RollbackResult",
    "Snapshotter", "RollbackEngine",
    # Mutation Context
    "MutationExecutionContext",
    # Sandbox Executor
    "SandboxWriteExecutor",
    "ENABLE_SANDBOX_WRITE", "DRY_RUN",
]
