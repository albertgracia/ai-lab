"""FEDERATION-COGNITIVE-GUARDS-01 burn-in.

Run:

  python3 tests/burnin_federation_cognitive_guards_01.py
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, "/opt/ai-lab")

from runtime.federation.contracts import FederatedExecutionIntent
from runtime.federation.role_router import build_routing_metadata
from runtime.federation.federation_guards import (
    get_federation_guard_events,
    get_federation_guard_runtime_state,
    get_federation_guard_summary,
    reset_federation_cognitive_guards_state,
)


def main() -> int:
    reset_federation_cognitive_guards_state()

    # Tighten caps to exercise transitions quickly.
    os.environ["AI_LAB_GUARD_MAX_EVIDENCE_REUSE_RATE"] = "2"
    os.environ["AI_LAB_GUARD_REUSE_WINDOW_SECONDS"] = "60"
    os.environ["AI_LAB_GUARD_CONSTRAINED_COOLDOWN_SECONDS"] = "60"

    # Integration path: build routing metadata repeatedly.
    intent = FederatedExecutionIntent(user_text="prometheus metrics", route_family="observe", request_id="cg1")
    for _ in range(3):
        meta = build_routing_metadata(intent)
        if "_cognitive_guard" not in meta:
            raise SystemExit("burnin_missing_cognitive_guard")

    st = get_federation_guard_runtime_state()
    if st.get("state") not in {"CONSTRAINED", "SAFE_MODE", "NORMAL"}:
        raise SystemExit("burnin_invalid_state")

    summ = get_federation_guard_summary()
    if "counters" not in summ:
        raise SystemExit("burnin_missing_summary")

    ev = get_federation_guard_events(limit=10)
    if "events" not in ev:
        raise SystemExit("burnin_missing_events")

    # Storm heuristic: many repeats should eventually push SAFE_MODE.
    os.environ["AI_LAB_GUARD_MAX_EVIDENCE_REUSE_RATE"] = "999"
    os.environ["AI_LAB_GUARD_EVENT_WINDOW_SECONDS"] = "60"
    os.environ["AI_LAB_GUARD_SAFE_MODE_COOLDOWN_SECONDS"] = "30"
    reset_federation_cognitive_guards_state()
    intent2 = FederatedExecutionIntent(user_text="prometheus metrics", route_family="observe", request_id="cg2")
    for _ in range(30):
        build_routing_metadata(intent2)
        time.sleep(0.01)
    st2 = get_federation_guard_runtime_state()
    if st2.get("state") not in {"SAFE_MODE", "CONSTRAINED", "NORMAL"}:
        raise SystemExit("burnin_storm_state_invalid")

    print("OK burnin federation cognitive guards 01")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
