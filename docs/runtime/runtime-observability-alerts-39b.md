# RUNTIME-OBSERVABILITY-ALERTS-39B

## Result

PASS.

## Scope

Observability and alerting layer for the stabilized AI-LAB runtime.

## Runtime baseline

- Gateway: OK
- Router: OK
- LM Studio chain: OK
- OpenCode Gateway contract: OK
- Graceful shutdown: active
- GitNexus Napi::Error: non-fatal
- GitNexus LangGraph recursion: external/blocked

## Metrics validated

- `ailab_gateway_shutdown_rejections_total`
- `ailab_slo_violations_total`
- `ailab_slo_degraded_total`
- `ailab_slo_safe_mode_total`
- `ailab_slo_gateway_health`
- `ailab_slo_lmstudio_health`
- `ailab_errors_total`
- `ailab_requests_total`
- `ailab_gateway_latency_p50_ms`
- `ailab_gateway_latency_p95_ms`

## Alerts added

| Alert | Metric | Severity | Purpose |
|---|---|---|---|
| `AILABGatewayDown` | `ailab_slo_gateway_health` | critical | Detect gateway unhealthy/down state from runtime SLO view. |
| `AILABGatewayShutdownRejections` | `increase(ailab_gateway_shutdown_rejections_total[5m])` | warning | Detect rejected requests during graceful shutdown windows. |
| `AILABGatewaySLOViolation` | `increase(ailab_slo_violations_total[10m])` | warning | Detect recent SLO violations affecting runtime quality. |
| `AILABGatewayHighErrorRate` | `rate(ailab_errors_total[5m])` | warning | Detect sustained local gateway error rate spikes. |

Rules file updated:

- `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml`

## Future alerts

These were intentionally not implemented because no authoritative metric is currently exposed:

- `AILABGatewayContractFailure` (requires explicit contract-failure metric or exporter)
- `AILABGitNexusStaleLongDuration` (requires stale-age metric from GitNexus index status)
- `AILABRuntimeExternalBlockedIssue` (documentation-only: external blocked state, not an on-box metric)

## Runbook

### AILABGatewayDown

- **Symptom:** `ailab_slo_gateway_health < 1`.
- **Likely cause:** gateway process down, bind failure, runtime internal failure.
- **First command:** `systemctl status ailab-gateway --no-pager`
- **Safe mitigation:** restart service and verify `curl -s http://127.0.0.1:8008/health | jq .`

### AILABGatewayShutdownRejections

- **Symptom:** increased `ailab_gateway_shutdown_rejections_total` in 5m.
- **Likely cause:** controlled restart/stop during active traffic.
- **First command:** `journalctl -u ailab-gateway -n 120 --no-pager`
- **Safe mitigation:** schedule restarts in low-traffic windows; ensure client retries are enabled.

### AILABGatewaySLOViolation

- **Symptom:** `increase(ailab_slo_violations_total[10m]) > 0`.
- **Likely cause:** latency spikes, upstream pressure, degraded inference backend.
- **First command:** `curl -s http://127.0.0.1:8008/metrics | grep 'ailab_slo_'`
- **Safe mitigation:** inspect gateway/router load and upstream reachability before restart.

### AILABGatewayHighErrorRate

- **Symptom:** `rate(ailab_errors_total[5m]) > 0.2`.
- **Likely cause:** malformed requests, upstream failures, transient backend errors.
- **First command:** `journalctl -u ailab-gateway -n 120 --no-pager`
- **Safe mitigation:** verify backend (`192.168.1.50:1234`) and re-check `/health`, `/v1/models`, `/v1/chat/completions`.

## Validation

- Prometheus rules check: `promtool` not available; YAML/rule placement reviewed manually.
- Runtime metrics check: PASS.
- Gateway health: PASS.
- Tests: not required in this phase (alerting/docs only).

## Conclusion

Observability alert coverage now includes explicit gateway-down, graceful-shutdown rejection, SLO violation, and gateway-error-rate monitoring.

Runtime remains stable and no functional runtime component changes were required.
