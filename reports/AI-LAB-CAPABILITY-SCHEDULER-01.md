# AI-LAB-CAPABILITY-SCHEDULER-01

**Classification:** PASS

**Date:** 2026-07-02

## Problem

When the gateway received a request for a model that requires a specific capability (vision, large-context, or a model that only exists on .60), the existing deterministic multi-node routing did not consider capability matching. Vision-capable models could be routed to text-only nodes, and rx7900xt-only models had no explicit routing logic to ensure they landed on .60.

## Solution

Capability Scheduler — a deterministic, explainable scheduling layer that runs BEFORE multi-node routing. Only activates for vision, large-context, or rx7900xt-required models. For normal chat/coding, it returns `skip` and the existing DNR handles routing.

### New file

`runtime/router/capability_scheduler.py` (651 lines)

- `extract_capability_requirements()` — deterministic extraction from model prefix, profile, route family, operator intent, message content
- `build_scheduler_candidates()` — builds candidate list from Dynamic Node Registry (online + routing-eligible only)
- `score_candidate()` — deterministic scoring with gates (rx7900xt requirement, capability match, model availability, health, SLO, role preference)
- `select_best_candidate()` — highest score wins. Tie-breaking: vision/large → .60, normal → .50
- `build_scheduler_decision()` — full pipeline: extract → candidates → score → select → decision

### Modified files

- `runtime/gateway/openai_gateway.py` — scheduler runs before DNR; route history records scheduler `reason_codes`; IFE-02/IFE-03 paths also include scheduler codes

## Design Decisions

### Only three capabilities trigger scheduling

Vision, large-context, and rx7900xt-required models need explicit node selection. Coding, reasoning, and embedding models exist on both .50 and .60 and should use DNR + fallback. This keeps the scheduler scope narrow and safe.

### Deterministic, not learned

No adaptive learning, no scoring weights tuned by feedback. All decisions are deterministic and explainable via `reason_codes[]`.

### No Prometheus metrics

Scheduler observability lives in route history `reason_codes[]`, not in Prometheus. Same pattern as the Intelligent Fallback Engine.

### Gateway integration: runs before DNR, not as replacement

Scheduler selects node for capability models. For `skip` decisions, DNR handles routing exactly as before.

## Tests

- 37 scheduler unit tests (extraction, candidate scoring, selection, SLO, output contract, reason codes, Hermes profile)
- 26 fallback engine tests (no regression)
- 38 DNR tests (no regression)
- **101/101 total PASS**

## Live Validation

| Test | Expected | Actual | Result |
|------|----------|--------|--------|
| Normal chat (qwen2.5-14b) | → .50 (DNR, scheduler skips) | rx9070-node | ✅ |
| Vision (moondream2-20250414) | → .60 (scheduler selected) | rx7900xt-node, codes=["scheduler_selected",...] | ✅ |
| Large (qwen3.6-35b-a3b) | → .60 (scheduler selected) | rx7900xt-node, codes=["scheduler_selected",...] | ✅ |
| Fallback still works | IFE triggers independently | intelligent_fallback visible in history | ✅ |
| Gateway UP | /health 200 | ok | ✅ |
| Prometheus | metrics available | 4 requests registered | ✅ |

## Next Steps

- Multi-GPU Scheduling (requires .60 node reactivation + pre-requisites)
- Validation Authority Recovery (37B) — restore Prometheus scrape targets
