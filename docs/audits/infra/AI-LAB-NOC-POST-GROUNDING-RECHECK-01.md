# AI-LAB NOC Post Grounding Recheck 01

## Result
- Verdict: PARTIAL
- Grounding regression: not reproduced
- Main critical cause remains: `no_nodes_online` / inference backend offline
- Additional review item: sensor fusion reports `unexpected_down: ai-lab-gateway` and recent journal noise includes a `BrokenPipeError` traceback

## Git
- Branch: `main`
- HEAD: `cdfe02eb`
- Working tree: clean before report creation
- Branch sync: `main...origin/main` with no ahead/behind markers before commit

## Systemd
- `systemctl --failed --no-pager`: no failed units
- Active AI-LAB services observed:
  - `ailab-docs.service`
  - `ailab-gateway.service`
  - `ailab-heartbeat.service`
  - `ailab-live-api.service`
  - `ailab-live-state.service`
  - `ailab-mcp-semantic-gateway.service`
  - `ailab-metrics.service`
  - `ailab-router.service`
  - `ailab-runner.service`
  - `gitnexus.service`

## Health Checks
- `http://127.0.0.1:8008/health`: `200`, gateway service healthy
- `http://127.0.0.1:8083/health`: `200`, router healthy
- `http://127.0.0.1:8084/health`: `{"error":"Not Found"}`; service is running but this endpoint is not exposed
- `http://127.0.0.1:4747/`: GitNexus UI root served successfully
- `http://127.0.0.1:6333/collections`: Qdrant collections returned successfully
- `http://127.0.0.1:4322/`: Astro docs homepage returned successfully

## Grounding Recheck
- `GET /runtime/grounding`: OK
- `contract_version`: `31E`
- `UNKNOWN_STATE_TOKENS`: absent
- `NameError`: absent
- `Traceback`: absent from the grounding response
- `unknown_state_semantics` present and stable:
  - `LOW_CONFIDENCE`
  - `NOT_OBSERVED`
  - `NO_RUNTIME_EVIDENCE`
  - `SOURCE_UNAVAILABLE`
  - `STALE_EVIDENCE`

## Runtime Health
- `GET /runtime/health/summary`: not exposed on this runtime; `GET /runtime/health` returned the active summary payload
- Overall health: `critical`
- Score: `0.0`
- Primary reason: `no_nodes_online`
- `nodes_online`: `0`
- `nodes_total`: `3`
- Watchdog: enabled
- Watchdog trigger: `no_nodes_online`
- GPU states:
  - `rx9070`: active
  - `rx7900xt`: inactive

## Sensors / Snapshot
- `GET /runtime/sensors`: OK
- `GET /runtime/sensors/summary`: not found
- Topology mode: `degraded_single_gpu`
- Active GPU: `RX9070` online
- Inventory offline GPU: `RX7900XT` expected offline
- Freshness: all observed sources reported fresh
- Sensor fusion also reported `unexpected_down: ai-lab-gateway`
- `lmstudio_models` source: low-confidence / unavailable

## Inference State
- Listening ports for inference backends: none detected on `1234`, `11434`, `5000`, `8000`
- No LM Studio / Ollama / vLLM / model-server process found
- Inference backend remains intentionally offline
- This is sufficient to explain the remaining `no_nodes_online` critical path

## Logs
- Gateway journal shows recent successful `GET /runtime/grounding` requests
- Gateway journal also contains a recent `BrokenPipeError` traceback
- No `UNKNOWN_STATE_TOKENS` or `NameError` found in the gateway logs searched for this recheck

## Metrics
- Gateway metrics exposed routing / SLO / grounding / critical health series successfully
- Observed metrics included:
  - `ailab_routing_decisions_total 0`
  - `ailab_slo_violations_total 4.0`
  - `ailab_slo_degraded_total 1.0`
  - `ailab_slo_safe_mode_total 1.0`
  - `ailab_slo_registry_consistency 1.0`
  - `ailab_slo_gateway_health 1.0`
  - `ailab_slo_lmstudio_health 1.0`
  - `ailab_cognitive_health_score 0.0`
  - `ailab_cognitive_health_nodes_online 0.0`
  - `ailab_cognitive_health_watchdog_triggers_total 49.0`
  - `ailab_critical_path_score 0.925`
  - `ailab_critical_path_unknowns_total 0.0`
  - `ailab_governance_drift_governance_confidence 0.721`
- Local Prometheus on `127.0.0.1:9090` was not reachable during this recheck

## Constraints Observed
- No services were restarted
- No inference backend was started
- No code or config was modified
- No push was performed
- No tag was created

## Residual Risks
- Sensor fusion still flags the gateway as `unexpected_down`
- Journal contains a recent `BrokenPipeError` traceback that should be watched if it repeats outside read-side log access
- Runtime remains `critical` until nodes come online

## Next Recommended Phase
- Investigate the sensor fusion / observability mismatch for `ai-lab-gateway`
- Keep the runtime grounding fix closed unless `NameError` reappears
