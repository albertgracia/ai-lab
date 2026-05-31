# AI-LAB Sensors Gateway Observability Discrepancy 01

## Result
- Verdict: PASS
- Gateway real: OK
- `runtime/sensors` discrepancy: not reproducible on a fresh read
- `BrokenPipeError`: classified as benign / client disconnect noise

## Git
- Branch: `main`
- HEAD: `d2152199`
- Working tree: clean before report creation
- Branch status: `main...origin/main [ahead 1]`

## Gateway Real State
- HTTP health: `200 OK`
- Metrics endpoint: responding
- `runtime/grounding`: clean, contract `31E`
- `runtime/health`: `critical` only because `no_nodes_online`
- `nodes_online`: `0`
- No runtime grounding regression observed

## systemd
- Unit: `ailab-gateway.service`
- `ActiveState=active`
- `SubState=running`
- `Result=success`
- `MainPID=171519`
- `ExecMainPID=171519`
- `NRestarts=1`
- `RestartUSec=5s`
- systemd and HTTP both show the gateway as healthy

## runtime/sensors
- Fresh read of `GET /runtime/sensors` returned:
  - `unexpected_down: []`
  - `gateway.health: ok`
  - `sensor_contract_version: 30I-D`
  - `topology_mode: degraded_single_gpu`
  - `freshness: 0.0s ago` for observed sources
- `GET /runtime/sensors/summary`: not found
- `GET /runtime/health/sensors`: `unknown_health_endpoint`
- `GET /runtime/health/summary`: runtime health payload returned correctly
- Earlier `unexpected_down: ai-lab-gateway` was not present in the fresh read

## Snapshot / Freshness
- `runtime/state/cluster_state.json` is stale relative to current gateway state and still records offline inference nodes
- `runtime/state/discovered_nodes.json` records LM Studio discovery failures for GPU nodes
- `runtime/state/topology_snapshot_31d.json` marks `ailab-gateway` as active
- The stale/offline node state explains `no_nodes_online`, not a gateway outage
- No persisted `unexpected_down: ai-lab-gateway` marker was found in `runtime/state`

## Name Mapping
- Expected sensor job name: `ai-lab-gateway`
- Prometheus gateway target: `job="ai-lab-gateway"`, `instance="192.168.1.30:8008"`, `up=1`
- systemd unit name: `ailab-gateway.service`
- No evidence of a naming bug causing the current gateway state

## BrokenPipeError Analysis
- Journal shows a `BrokenPipeError` at `14:56:02`
- Stack trace points to `self.wfile.write(prom_text.encode("utf-8"))` while serving `GET /metrics`
- Request was from `127.0.0.1:58692`
- Pattern fits a client closing the connection during a metrics response
- Frequency in the last 2 hours: `BrokenPipeError=14`, `Traceback=14`
- This is noisy, but it did not break health, grounding, or metrics serving

## Prometheus
- Remote Prometheus query showed `up` for `ai-lab-gateway` as `1`
- Remote Prometheus query for gateway requests metric returned no data, which is consistent with low/zero request volume
- Prometheus output contradicts a persistent gateway-down condition

## Cause Classification
- Primary cause: B, stale snapshot / transient state during restart window
- Secondary cause: E, benign BrokenPipe noise from client disconnect
- Not supported by evidence: A, C, D, F

## Operational Risk
- Low
- The gateway is up and serving correctly
- The only remaining runtime critical path is the expected `no_nodes_online` inference-backend condition

## No-Touch Confirmation
- No services were restarted
- No inference backend was started
- No code or config was modified
- No push was performed
- No tag was created

## Recommended Next Phase
- Optional follow-up: reduce `/metrics` BrokenPipe noise if it becomes frequent enough to obscure logs
- Keep the grounding fix closed; no regression observed
