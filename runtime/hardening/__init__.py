from runtime.hardening.runtime_operational_hardening import (
    build_runtime_hardening_report,
    build_runtime_watchdogs,
    build_timeout_governance,
    build_degraded_escalation,
    build_runtime_survivability,
    build_failure_containment_summary,
    build_operational_safeguards,
    calculate_hardening_score,
    detect_operational_instability,
)
from runtime.hardening.contracts import (
    RuntimeHardeningContract,
    WatchdogContract,
    TimeoutGovernanceContract,
    DegradedEscalationContract,
    FailureContainmentContract,
    OperationalSafeguardContract,
    RuntimeSurvivabilityContract,
)

HARDENING_CONTRACT_VERSION = "34A"
