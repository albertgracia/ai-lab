from runtime.gc.crossplan_gc import (
    build_gc_inventory,
    detect_gc_candidates,
    protect_governance_artifacts,
    protect_active_validation_artifacts,
    protect_runtime_authority_artifacts,
    calculate_gc_safety_score,
    build_gc_execution_plan,
)

GC_CONTRACT_VERSION = "28.4"
