from __future__ import annotations

from enum import Enum
from runtime.errors.taxonomy import RuntimeErrorCategory


class Recoverability(str, Enum):
    AUTO_RECOVERABLE = "auto_recoverable"
    RETRYABLE = "retryable"
    MANUAL_INTERVENTION = "manual_intervention"
    NON_RECOVERABLE = "non_recoverable"


RECOVERABILITY_MAP: dict[RuntimeErrorCategory, Recoverability] = {
    RuntimeErrorCategory.STREAM_INTERRUPTED: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.CLIENT_DISCONNECT: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.CONCURRENCY_THROTTLE: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.MEMORY_EMPTY: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.LMSTUDIO_TIMEOUT: Recoverability.RETRYABLE,
    RuntimeErrorCategory.UPSTREAM_TIMEOUT: Recoverability.RETRYABLE,
    RuntimeErrorCategory.UPSTREAM_CONNECTION: Recoverability.RETRYABLE,
    RuntimeErrorCategory.LMSTUDIO_STREAM_STALL: Recoverability.RETRYABLE,
    RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE: Recoverability.RETRYABLE,
    RuntimeErrorCategory.STREAM_BACKPRESSURE: Recoverability.RETRYABLE,
    RuntimeErrorCategory.MEMORY_RECALL_FAILURE: Recoverability.RETRYABLE,
    RuntimeErrorCategory.ROLLBACK_FAILURE: Recoverability.MANUAL_INTERVENTION,
    RuntimeErrorCategory.WORKFLOW_INVALID_STATE: Recoverability.MANUAL_INTERVENTION,
    RuntimeErrorCategory.SANDBOX_POLICY_BLOCK: Recoverability.MANUAL_INTERVENTION,
    RuntimeErrorCategory.GATEWAY_INTERNAL: Recoverability.MANUAL_INTERVENTION,
    RuntimeErrorCategory.MODEL_DISABLED: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.PROMPT_POLICY: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.TOOL_VALIDATION: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.REQUEST_VALIDATION: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.REQUEST_TOO_LARGE: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.GOVERNANCE_BLOCK: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.PROMPT_SANITIZATION: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.TOOL_MALFORMED: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.TOOL_PARALLEL_UNSUPPORTED: Recoverability.RETRYABLE,
    RuntimeErrorCategory.EXECUTOR_READONLY_BLOCK: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.SANDBOX_TRAVERSAL_ATTEMPT: Recoverability.NON_RECOVERABLE,
    RuntimeErrorCategory.ROUTING_FAILURE: Recoverability.RETRYABLE,
    RuntimeErrorCategory.GPU_PRESSURE: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.VRAM_PRESSURE: Recoverability.AUTO_RECOVERABLE,
    RuntimeErrorCategory.UNKNOWN: Recoverability.MANUAL_INTERVENTION,
}


def recoverability_for_category(cat: RuntimeErrorCategory) -> Recoverability:
    return RECOVERABILITY_MAP.get(cat, Recoverability.MANUAL_INTERVENTION)
