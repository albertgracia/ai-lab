from __future__ import annotations

import copy
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any

from runtime.errors.taxonomy import RuntimeErrorCategory
from runtime.errors.severity import ErrorSeverity, severity_for_category
from runtime.errors.recovery import Recoverability, recoverability_for_category
from runtime.errors.correlation import CorrelationTags, new_error_id, stack_hash


ORIGIN_STAGES: frozenset[str] = frozenset({
    "routing", "classification", "streaming", "upstream",
    "governance", "agentic", "sandbox", "rollback",
    "reporting", "memory", "observability",
})

EXCLUDED_FROM_LOG: frozenset[str] = frozenset({
    "client_ip",
})


@dataclass
class RuntimeErrorEvent:
    error_id: str = ""
    timestamp: float = 0.0
    category: RuntimeErrorCategory = RuntimeErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.ERROR
    recoverability: Recoverability = Recoverability.MANUAL_INTERVENTION
    origin_stage: str = "gateway"
    component: str = "gateway"
    source_file: str = ""
    workflow_id: str | None = None
    request_id: str | None = None
    model: str | None = None
    route_type: str | None = None
    client_ip: str | None = None
    message: str = ""
    root_cause: str = ""
    exception_class: str = ""
    stack_hash: str = ""
    latency_ms: float | None = None
    streaming: bool = False
    retryable: bool = True
    slo_impact: bool = False
    degradation_related: bool = False
    correlation_tags: dict[str, str] = field(default_factory=dict)
    first_seen: float | None = None
    last_seen: float | None = None
    occurrence_count: int = 1

    def __post_init__(self) -> None:
        if not self.error_id:
            self.error_id = new_error_id()
        if not self.timestamp:
            self.timestamp = time.time()
        if isinstance(self.category, str):
            self.category = RuntimeErrorCategory(self.category)
        self.severity = severity_for_category(self.category)
        self.recoverability = recoverability_for_category(self.category)
        self.retryable = self.recoverability in (
            Recoverability.RETRYABLE,
            Recoverability.AUTO_RECOVERABLE,
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        d["recoverability"] = self.recoverability.value
        for skip in EXCLUDED_FROM_LOG:
            d.pop(skip, None)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    def to_prometheus_labels(self) -> dict[str, str]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "component": self.component,
        }

    @classmethod
    def from_exception(
        cls,
        exc: BaseException,
        *,
        category: RuntimeErrorCategory | None = None,
        origin_stage: str = "gateway",
        component: str = "gateway",
        source_file: str = "",
        workflow_id: str | None = None,
        request_id: str | None = None,
        model: str | None = None,
        route_type: str | None = None,
        streaming: bool = False,
        slo_impact: bool = False,
        message: str = "",
        **kw: Any,
    ) -> RuntimeErrorEvent:
        import traceback
        tb_str = traceback.format_exc()
        ev = cls(
            category=category or RuntimeErrorCategory.UNKNOWN,
            origin_stage=origin_stage,
            component=component,
            source_file=source_file or cls._source_file(),
            workflow_id=workflow_id,
            request_id=request_id,
            model=model,
            route_type=route_type,
            streaming=streaming,
            slo_impact=slo_impact,
            message=message or str(exc)[:500],
            root_cause=str(exc)[:500],
            exception_class=type(exc).__name__,
            stack_hash=stack_hash(tb_str),
            **kw,
        )
        return ev

    @staticmethod
    def _source_file() -> str:
        import inspect
        frame = inspect.currentframe()
        while frame:
            fname = frame.f_code.co_filename
            if "runtime/errors/" not in fname:
                return fname
            frame = frame.f_back
        return ""
