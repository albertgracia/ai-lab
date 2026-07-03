# Intelligent Fallback Engine (IFE)

## Purpose

Deterministic fallback strategy when a model request fails on the primary node. IFE classifies the failure, builds a candidate list from the Dynamic Node Registry, selects the best fallback candidate respecting capability safety, and retries the request.

IFE does NOT replace multi-node routing. It is a safety net when deterministic routing selects a node that fails at runtime.

## Design Constraints

- **No scheduler** — IFE does not start/stop nodes or migrate models.
- **No silent unsafe degradation** — Vision models never fall back to text-only nodes. Large-context models never fall back to small-context nodes.
- **No Prometheus metrics** — IFE observability lives in route history / control plane, not in Prometheus. (The existing `ailab_fallback_leakage_blocked_total` metric is from the FASE 30H.1 evidence guard, not IFE.)
- **Non-streaming fallback** — When fallback occurs, the response is always non-streaming (pops `stream` from payload). This is safe degradation: client gets a valid response instead of an error.
- **Single attempt** — IFE tries exactly one fallback candidate. If the fallback also fails, the original error is returned.

## Failure Classification

| Failure Type | Retryable | Fallback Allowed | Same Model Required | Safe Degrade Allowed | Description |
|---|---|---|---|---|---|
| `node_offline` | ✅ | ✅ | ❌ | ✅ | Node unreachable (connection refused, DNS failure) |
| `backend_timeout` | ✅ | ✅ | ❌ | ✅ | Request timed out at the inference backend |
| `backend_connection_error` | ✅ | ✅ | ❌ | ✅ | Connection error to inference backend |
| `model_not_loaded` | ✅ | ✅ | ✅ | ❌ | Model exists on node but not loaded in VRAM |
| `model_not_available_on_node` | ❌ | ✅ | ❌ | ❌ | Model does not exist on this node at all |
| `http_5xx` | ✅ | ✅ | ❌ | ✅ | Backend returned 5xx status |
| `context_overflow` | ❌ | ❌ | — | — | Request exceeds model context window |
| `rate_limited` | ✅ | ✅ | ❌ | ✅ | Backend rate-limited the request |
| `capacity_unavailable` | ❌ | ❌ | — | — | No eligible fallback nodes with capacity |
| `unknown_backend_error` | ❌ | ❌ | — | — | Unclassifiable backend error |

## Candidate Building & Selection

`build_fallback_candidates(requested_model, failed_node_id, registry)`:

1. Filter registry entries where `fallback_eligible == True` and `node_id != failed_node_id`
2. Order by preference: same model > equivalent model > capability match
3. Assign priority score (higher = preferred)

`select_fallback_candidate(candidates, requested_model)`:

- Vision models (`moondream2`, `qwen-vl`, `llava`, `phi-vision`) → only fall back to nodes that also host vision models
- Large-context models (`30b`, `32b`, `35b`, `xl`, `qwen3.6`) → only fall back to nodes with large-context models
- Coding models (`qwen2.5-coder`, `qwen3-coder`) → only fall back to nodes with coding models
- Reasoning models (`deepseek-r1`, `deepseek-reasoner`) → only fall back to nodes with reasoning models
- If no safe candidate: return `None` and the gateway returns `capacity_unavailable` error

## Gateway Integration

In `runtime/gateway/openai_gateway.py`, the `_try_fallback()` helper:

1. Takes `(requested_model, failed_node_id, error_message, response_status, response_body, registry, backend_urls)`
2. Classifies the failure via `classify_backend_failure()`
3. If `fallback_allowed == True`:
   - Builds candidates via `build_fallback_candidates()`
   - Selects candidate via `select_fallback_candidate()`
   - If candidate found: POST to fallback backend (non-streaming), records `_fallback_info` in `locals()`
4. Returns `(success, response_or_error, fallback_info)`

### Integration Points

- **IFE-01** — After 400+ POST response (after existing "model unloaded" retry in non-streaming path)
- **IFE-02** — In `except RequestException` before returning 502
- **IFE-03** — In `except Exception` before returning 500

## Route History / Control Plane Exposure

Every route entry records these fallback fields:

| Field | Type | Description |
|---|---|---|
| `fallback_triggered` | bool | Whether fallback was attempted |
| `failure_type` | str | Classified failure type |
| `original_model` | str | Model requested by client |
| `original_node` | str | Node that was selected by routing |
| `fallback_model` | str | Model used after fallback |
| `fallback_node` | str | Node that served the fallback |
| `fallback_reason` | str | Human-readable fallback reason |
| `reason_codes` | list[str] | Machine-readable reason codes |

## Metrics

IFE does NOT add Prometheus metrics. The existing `ailab_fallback_leakage_blocked_total` metric (from FASE 30H.1 universal evidence guard) is unrelated.

Fallback observability is via:
- **Route history** (`/api/control/routes`) — all fallback fields listed above
- **Control plane explain** — `explain_last_route()` includes fallback info

## Module

`runtime/router/fallback_engine.py`

### Pure Functions

| Function | Returns | Description |
|---|---|---|
| `classify_backend_failure(response_status, response_body, exception, error_message)` | dict | Failure type + policy flags |
| `build_fallback_candidates(requested_model, failed_node_id, registry)` | list[dict] | Ordered candidates by preference |
| `select_fallback_candidate(candidates, requested_model)` | dict or None | Best candidate or None |
| `build_capacity_unavailable_error(requested_model, failed_node_id, failure_type, detail)` | dict | Error response dict |

## Contract Version

`INTELLIGENT-FALLBACK-ENGINE-01`
