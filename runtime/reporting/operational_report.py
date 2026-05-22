from __future__ import annotations

from typing import Any

from runtime.reporting.contracts import (
    REPORTING_CONTRACT_VERSION,
    OperationalReportContract,
)
from runtime.reporting.reporting_engine import build_operational_report as _build

REPORTING_CONTRACT_VERSION = REPORTING_CONTRACT_VERSION


def build_operational_report(
    sensor_snapshot: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
    mode: str = "compact",
) -> dict[str, Any]:
    return _build(
        sensor_snapshot=sensor_snapshot,
        maturity=maturity,
        mode=mode,
    )
