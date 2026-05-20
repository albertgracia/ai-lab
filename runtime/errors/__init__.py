from runtime.errors.taxonomy import RuntimeErrorCategory, ALL_CATEGORIES
from runtime.errors.severity import ErrorSeverity, severity_for_category
from runtime.errors.recovery import Recoverability, recoverability_for_category
from runtime.errors.correlation import CorrelationTags, new_error_id, stack_hash, dedup_key
from runtime.errors.runtime_errors import RuntimeErrorEvent, ORIGIN_STAGES
from runtime.errors.attribution import (
    classify_exception,
    classify_http_status,
    classify_stream_failure,
    classify_timeout,
    classify_timeout_stage,
    infer_root_cause,
    build_error_event,
)
from runtime.errors.metrics import emit_error, emit_structured_log, emit_prometheus

__all__ = [
    "RuntimeErrorCategory",
    "ALL_CATEGORIES",
    "ErrorSeverity",
    "severity_for_category",
    "Recoverability",
    "recoverability_for_category",
    "CorrelationTags",
    "new_error_id",
    "stack_hash",
    "dedup_key",
    "RuntimeErrorEvent",
    "ORIGIN_STAGES",
    "classify_exception",
    "classify_http_status",
    "classify_stream_failure",
    "classify_timeout",
    "classify_timeout_stage",
    "infer_root_cause",
    "build_error_event",
    "emit_error",
    "emit_structured_log",
    "emit_prometheus",
]
