from __future__ import annotations

from enum import Enum
from runtime.errors.taxonomy import RuntimeErrorCategory


class ErrorSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


SEVERITY_MAP: dict[RuntimeErrorCategory, ErrorSeverity] = {
    RuntimeErrorCategory.CLIENT_DISCONNECT: ErrorSeverity.INFO,
    RuntimeErrorCategory.MEMORY_EMPTY: ErrorSeverity.INFO,
    RuntimeErrorCategory.STREAM_BACKPRESSURE: ErrorSeverity.INFO,
    RuntimeErrorCategory.LMSTUDIO_TIMEOUT: ErrorSeverity.WARNING,
    RuntimeErrorCategory.LMSTUDIO_STREAM_STALL: ErrorSeverity.WARNING,
    RuntimeErrorCategory.STREAM_INTERRUPTED: ErrorSeverity.WARNING,
    RuntimeErrorCategory.CONCURRENCY_THROTTLE: ErrorSeverity.WARNING,
    RuntimeErrorCategory.MEMORY_RECALL_FAILURE: ErrorSeverity.WARNING,
    RuntimeErrorCategory.TOOL_MALFORMED: ErrorSeverity.WARNING,
    RuntimeErrorCategory.TOOL_PARALLEL_UNSUPPORTED: ErrorSeverity.WARNING,
    RuntimeErrorCategory.PROMPT_POLICY: ErrorSeverity.WARNING,
    RuntimeErrorCategory.PROMPT_SANITIZATION: ErrorSeverity.WARNING,
    RuntimeErrorCategory.UPSTREAM_TIMEOUT: ErrorSeverity.ERROR,
    RuntimeErrorCategory.UPSTREAM_CONNECTION: ErrorSeverity.ERROR,
    RuntimeErrorCategory.UPSTREAM_INVALID_RESPONSE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.LMSTUDIO_MODEL_UNAVAILABLE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.REQUEST_VALIDATION: ErrorSeverity.ERROR,
    RuntimeErrorCategory.REQUEST_TOO_LARGE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.GOVERNANCE_BLOCK: ErrorSeverity.ERROR,
    RuntimeErrorCategory.TOOL_VALIDATION: ErrorSeverity.ERROR,
    RuntimeErrorCategory.WORKFLOW_INVALID_STATE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.EXECUTOR_READONLY_BLOCK: ErrorSeverity.ERROR,
    RuntimeErrorCategory.SANDBOX_POLICY_BLOCK: ErrorSeverity.ERROR,
    RuntimeErrorCategory.SANDBOX_TRAVERSAL_ATTEMPT: ErrorSeverity.ERROR,
    RuntimeErrorCategory.ROLLBACK_FAILURE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.ROUTING_FAILURE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.MODEL_DISABLED: ErrorSeverity.ERROR,
    RuntimeErrorCategory.GPU_PRESSURE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.VRAM_PRESSURE: ErrorSeverity.ERROR,
    RuntimeErrorCategory.GATEWAY_INTERNAL: ErrorSeverity.CRITICAL,
    RuntimeErrorCategory.COMPLETION_TRUNCATED: ErrorSeverity.WARNING,
    RuntimeErrorCategory.UNKNOWN: ErrorSeverity.ERROR,
}


def severity_for_category(cat: RuntimeErrorCategory) -> ErrorSeverity:
    return SEVERITY_MAP.get(cat, ErrorSeverity.ERROR)
