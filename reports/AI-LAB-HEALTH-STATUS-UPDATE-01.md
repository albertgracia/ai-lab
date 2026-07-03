# AI-LAB-HEALTH-STATUS-UPDATE-01

## Executive Summary

AI-LAB runtime is **operational with warnings**. The control plane and inference backends are serving traffic, observability stack is collecting metrics, and GPU exporters are back online. One critical issue: `ailab-live-api` (port 8084) is not responding on any path (404). Loki ingester is stuck in "not ready" state.

---

## Overall Health Score

| Category | Score | Status |
|----------|-------|--------|
| Infrastructure (Control Plane) | 4/5 | ⚠️ Live API down |
| Observability Stack | 4/5 | ⚠️ Loki stuck |
| Inference | 5/5 | ✅ Full operational |
| Developer Platform | 4/5 | ⚠️ MCP limited |
| **Composite** | **17/20** | **PASS WITH WARNINGS** |

---

## Infrastructure — Control Plane (192.168.1.30)

| Component | Port | Status | Evidence |
|-----------|------|--------|----------|
| Gateway | 8008 | **PASS** | /health returns `{"status":"ok","service":"ai-lab-openai-gateway"}` (HTTP 200). /metrics returns HTTP 200. |
| Router | 8083 | **PASS** | /health returns `{"status":"ok","service":"ai-lab-router-api"}` (HTTP 200). /metrics returns HTTP 200. |
| Live API | 8084 | **FAIL** | /health, /, /api/health all return `{"error":"Not Found"}` (HTTP 404). Server alive but no valid endpoint exposed. |
| Node Exporter | 9100 | **PASS** | /metrics returns HTTP 200. Prometheus scrapes successfully. |
| cAdvisor | 8081 | **PASS** | /metrics returns HTTP 200. Prometheus scrapes successfully. |

---

## Observability Stack (192.168.1.40)

| Component | Port | Status | Evidence |
|-----------|------|--------|----------|
| Prometheus | 9090 | **PASS** | /-/healthy: "Prometheus Server is Healthy." All 17 active targets UP. 3 rule groups (47 rules), all health=ok. 0 alerts firing. |
| Grafana | 3000 | **PASS** | /api/health: `{"database":"ok","version":"13.0.1"}`. |
| Loki | 3100 | **PASS WITH WARNINGS** | Server responds (version 3.7.1), but /ready reports "Ingester not ready: waiting for 15s after being ready" — stuck state. |
| Node Exporter | 9100 | **PASS** | /metrics returns HTTP 200. Prometheus scrapes successfully. |

---

## Inference — LM Studio (192.168.1.50)

| Check | Port | Status | Evidence |
|-------|------|--------|----------|
| LM Studio API | 1234 | **PASS** | /v1/models returns 6 models (HTTP 200). Models: google/gemma-4-12b, qwen2.5-14b-instruct, qwen/qwen3.6-27b, deepseek-coder-v2-lite-instruct, deepseek/deepseek-r1-distill-qwen-14b, text-embedding-nomic-embed-text-v1.5. |
| TCP reachable | 1234 | **PASS** | TcpTestSucceeded: True. |

---

## GPU Observability

### RX9070 Node (192.168.1.50)

| Exporter | Port | Status | Evidence | Prometheus Target |
|----------|------|--------|----------|-------------------|
| windows_exporter | 9182 | **PASS** | /metrics (HEAD) returns HTTP 200. | ai-lab-gpu-rx9070 — UP (lastScrape: 0.023s, no error) |
| LibreHardwareMonitor | 9183 | **PASS** | /metrics (HEAD) returns HTTP 200 (Microsoft-HTTPAPI/2.0). | ai-lab-gpu-metrics — UP (lastScrape: 0.244s, no error) |

### RX7900XT Node (192.168.1.60)

| Exporter | Port | Status | Evidence | Prometheus Target |
|----------|------|--------|----------|-------------------|
| windows_exporter | 9182 | **PASS** | /metrics (HEAD) returns HTTP 200. | ai-lab-gpu-rx7900xt — UP (lastScrape: 0.022s, no error) |
| LibreHardwareMonitor | 9183 | **PASS** | /metrics (HEAD) returns HTTP 200 (Microsoft-HTTPAPI/2.0). | ai-lab-gpu-metrics — UP (lastScrape: 0.122s, no error) |

---

## Prometheus Target Summary

All 17 targets across 11 scrape pools are **UP**:

| Target | Instance | Health | Last Scrape Duration |
|--------|----------|--------|---------------------|
| ai-lab-cadvisor | 192.168.1.30:8081 | UP | 3.6ms |
| ai-lab-gateway | 192.168.1.30:8008 | UP | 46.8ms |
| ai-lab-gpu-metrics (.50) | 192.168.1.50:9183 | UP | 243.8ms |
| ai-lab-gpu-metrics (.60) | 192.168.1.60:9183 | UP | 121.8ms |
| ai-lab-gpu-rx9070 | 192.168.1.50:9182 | UP | 23.3ms |
| ai-lab-gpu-rx7900xt | 192.168.1.60:9182 | UP | 22.5ms |
| ai-lab-live-api | 192.168.1.30:8084 | UP | 3.8ms |
| ai-lab-node | 192.168.1.30:9100 | UP | 36.7ms |
| ai-lab-router | 192.168.1.30:8083 | UP | 4.4ms |
| cloudflare-tunnel | cloudflare-tunnel:2000 | UP | 2.3ms |
| docker | cadvisor:8080 | UP | 184.3ms |
| ubuntu-server | 192.168.1.40:9100 | UP | 19.8ms |
| unpoller | 192.168.1.40:9130 | UP | 1.05s |
| windows11-nas | 192.168.1.200:9182 | UP | 47.9ms |
| + 3 more non-AI-LAB targets | — | UP | — |

**47 rules** across 3 groups (23 alerts + 5 recording + 19 route-family alerts) — all health=ok, all alerts inactive.

---

## GitNexus Operational Status

| Check | Status | Evidence |
|-------|--------|----------|
| Repository indexed | **PASS** | ai-lab repo indexed (1069 files, 22746 nodes, 34230 edges, 484 communities, 300 processes). |
| Index freshness | **PASS** | Indexed at 2026-06-30T10:23:04Z. Last commit: 31b5bd59. Index is ~14 hours old. |
| MCP connectivity | **PASS** | GitNexus resource templates available (schema, clusters, processes). |

---

## MCP Server Status

| Server | Status | Evidence |
|--------|--------|----------|
| gitnexus | **PASS** | Connected. Resources and templates available. |
| ailab-runtime-mcp | **PASS WITH WARNINGS** | Server is configured but returned empty resource list. Tools are available per configuration. |

---

## OpenCode Capabilities

| Capability | Status | Evidence |
|------------|--------|----------|
| HTTP requests | **PASS** | curl.exe, python, node all functioning. HTTP 200 from multiple endpoints. |
| PowerShell execution | **PASS** | PowerShell 5.1 operational. Commands executed successfully throughout this session. |
| GitNexus access | **PASS** | Repo listing, context query, resource templates all accessible. |

---

## Final Table

| Component | Status | Evidence | Method |
|-----------|--------|----------|--------|
| Gateway :8008 | **PASS** | `{"status":"ok"}` | HTTP GET /health |
| Router :8083 | **PASS** | `{"status":"ok"}` | HTTP GET /health |
| Live API :8084 | **FAIL** | 404 on all paths | HTTP GET /health, /, /api/health |
| Node Exporter :9100(.30) | **PASS** | HTTP 200 on /metrics | HTTP GET /metrics |
| cAdvisor :8081 | **PASS** | HTTP 200 on /metrics | Prometheus scrape |
| Prometheus :9090 | **PASS** | "Prometheus Server is Healthy" | HTTP GET /-/healthy |
| Grafana :3000 | **PASS** | `{"database":"ok"}` | HTTP GET /api/health |
| Loki :3100 | **PASS WITH WARNINGS** | /ready stuck, but build info responds | HTTP GET /ready, /buildinfo |
| LM Studio :1234 | **PASS** | 6 models, HTTP 200 | HTTP GET /v1/models |
| RX9070 exporter :9182 | **PASS** | HTTP 200, Prometheus UP | HTTP HEAD /metrics |
| RX9070 sensor :9183 | **PASS** | HTTP 200, Prometheus UP | HTTP HEAD /metrics |
| RX7900XT exporter :9182 | **PASS** | HTTP 200, Prometheus UP | HTTP HEAD /metrics |
| RX7900XT sensor :9183 | **PASS** | HTTP 200, Prometheus UP | HTTP HEAD /metrics |
| GitNexus | **PASS** | 22746 symbols indexed | API listing & context |
| MCP (gitnexus) | **PASS** | Resources/templates connected | MCP resource listing |
| MCP (ailab-runtime) | **PASS WITH WARNINGS** | Configured, empty resource list | MCP resource listing |
| OpenCode HTTP | **PASS** | curl.exe, python, node functional | Multiple HTTP tests |
| OpenCode PowerShell | **PASS** | PS 5.1 operational | Multiple command tests |
| OpenCode GitNexus | **PASS** | All gitnexus tools functional | Tool execution |

---

## Operational Risks

1. **Live API (8084) — Failing**: 404 on every path. Service is running (Prometheus scrapes /metrics) but no HTTP handler path is responding. This breaks runtime state queries, operator summaries, and precision endpoints that rely on this service.

2. **Loki — Ingester Stuck**: /ready reports "Ingester not ready: waiting for 15s after being ready" — likely a persistent stuck state. Log collection may be impaired.

3. **Grafana credentials**: Default admin credentials did not work for datasource query (401/403 expected but not confirmed). Dashboard configuration access may be limited.

4. **WinRM blocked**: Cannot remotely inspect scheduled tasks on Windows nodes (.50, .60). No evidence that GPU exporters are configured as persistent services — they could be manually launched and crash-prone.

---

## Current Warnings

- Loki ingester not ready (stuck state)
- Grafana admin access unverified
- Live API endpoint failure (impact: runtime state queries)
- MCP ailab-runtime server resource listing empty (tools may still work)

---

## Current Failures

- **ailab-live-api (192.168.1.30:8084)**: All paths return 404. Service is running but not serving. Immediate action recommended.

---

## Current Unknowns

- Whether WinRM/firewall rules on .50 and .60 allow remote service management.
- Whether Grafana dashboards are accessible (credentials unknown).
- Whether Loki is actually ingesting logs despite /ready stuck state.
- Scheduled tasks status on GPU nodes (WinRM blocked).

---

## Final Conclusion

**Status: PASS WITH WARNINGS**

AI-LAB is operational. The inference backend, GPU metrics collection, Prometheus observability, and control plane gateway are all functioning correctly. The previous GPU exporter outage has been resolved — all four GPU targets (RX9070 + RX7900XT on both 9182/9183) are scraping successfully.

Two issues need attention:
1. **ailab-live-api port 8084** — service runs but serves no content.
2. **Loki ingester** — stuck in pre-ready state.

No inference degradation. No model availability issues. No scrape failures in Prometheus.

**Date: 2026-06-30 19:09 UTC-5**
