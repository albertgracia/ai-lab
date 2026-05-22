from runtime.plans.plan_registry import (
    build_plan_registry,
    build_cross_plan_references,
    build_plan_dependencies,
    build_plan_lifecycle_summary,
    detect_orphan_plans,
    detect_stale_plans,
    detect_invalid_plan_references,
)

PLAN_CONTRACT_VERSION = "28.4"
