"""Tool Reliability Metrics — prometheus_client counters for tool-use observability.

Exports:
  TOOL_MALFORMED  — parse failures
  TOOL_BLOCKED    — blocked by safety policy (reuses GOVERNANCE_BLOCKED)
  TOOL_FASTPATH   — tool fastpath activations
  TOOL_FASTPATH_FALLBACK — fastpath that fell back to normal routing
"""

from prometheus_client import Counter

TOOL_MALFORMED = Counter(
    "ailab_tool_calls_malformed_total",
    "Numero de tool calls con parseo fallido desde LM Studio",
)

TOOL_FASTPATH = Counter(
    "ailab_tool_fastpath_total",
    "Numero de peticiones tool_use procesadas via fastpath",
)

TOOL_FASTPATH_FALLBACK = Counter(
    "ailab_tool_fastpath_fallback_total",
    "Numero de peticiones tool_use que cayeron al routing normal",
)
