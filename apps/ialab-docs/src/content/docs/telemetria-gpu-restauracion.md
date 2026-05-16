---
title: "Restauración de telemetría GPU y verificación de dashboards"
summary: "Diagnóstico y reparación de target Prometheus caído en RX9070 (9183), corrección de etiquetas en exporter GPU, y verificación de los 9 dashboards AI-LAB en Grafana."
order: 27
---

## Síntoma

Target `192.168.1.50:9183` en Prometheus reportado como caído:

```json
"health": "down",
"lastError": "Get \"http://192.168.1.50:9183/metrics\": context deadline exceeded"
```

## Diagnóstico

El puerto 9183 lo servía un script PowerShell (`gpu_metrics.ps1`) con `HttpListener` que lee sensores GPU vía `LibreHardwareMonitorLib.dll`. El proceso se había caído y al restaurarlo se descubrieron problemas adicionales.

## Problemas encontrados y soluciones

| # | Problema | Causa | Solución |
|---|---|---|---|
| 1 | Puerto 9183 no accesible desde red local | Firewall de Windows bloqueando tráfico entrante | `netsh advfirewall firewall add rule name="GPU Metrics 9183" dir=in action=allow protocol=TCP localport=9183` |
| 2 | Métricas rechazadas por Prometheus | Etiquetas sin quotes: `gpu=RX9070` en lugar de `gpu="RX9070"` | Añadido `[char]34` alrededor de valores en `gpu_metrics.ps1` |
| 3 | Task programada GPUExporter no se reiniciaba | Procesos PowerShell huérfanos bloqueando el puerto | Matar procesos y reiniciar vía `schtasks /run /tn GPUExporter` |

## Arquitectura del exporter GPU

```
GPUExporter (scheduled task, cada 1 min)
  └─ wscript.exe → start_hidden.vbs
       └─ powershell.exe → gpu_metrics.ps1
            └─ HttpListener en :9183 con LibreHardwareMonitorLib.dll
                 └─ /metrics → sensores GPU (temp, load, clock, power, D3D)

GPUSensorCollector (scheduled task, cada 1 min)
  └─ powershell.exe → get_gpu_sensors.ps1
       └─ Out-File → textfile/gpu_sensors.prom
```

## Fix adicional: encoding en get_gpu_sensors.ps1

El script `get_gpu_sensors.ps1` usaba `Out-File` sin `-Encoding ascii`, generando el fichero en UTF-16 LE. Prometheus no puede parsear UTF-16. Se añadió `-Encoding ascii` a todas las líneas `Out-File`.

## Verificación de dashboards Grafana

**Servidor**: `192.168.1.40:3000` (Grafana v13.0.1)

### Targets Prometheus — 14/14 UP

| Grupo | Targets | Health |
|---|---|---|
| `ai-lab-gpu-metrics` | `192.168.1.50:9183`, `192.168.1.60:9183` | ✅ UP |
| `ai-lab-gpu-rx9070` | `192.168.1.50:9182` | ✅ UP |
| `ai-lab-gpu-rx7900xt` | `192.168.1.60:9182` | ✅ UP |
| `ai-lab-node` | `192.168.1.30:9100` | ✅ UP |
| `ubuntu-server` | `192.168.1.40:9100` | ✅ UP |
| `ai-lab-gateway` | `192.168.1.30:8008` | ✅ UP |
| `ai-lab-cadvisor` | `192.168.1.30:8081` | ✅ UP |
| `docker` | `cadvisor:8080` | ✅ UP |
| `cloudflare-tunnel` | `cloudflare-tunnel:2000` | ✅ UP |
| `windows11-nas` | `192.168.1.200:9182` | ✅ UP |
| `serv2025-hyperv2` | `192.168.1.100:9182` | ✅ UP |
| `serv2025-market` | `192.168.1.150:9182` | ✅ UP |
| `unpoller` | `192.168.1.40:9130` | ✅ UP |

### Dashboards en carpeta AI-LAB

| Dashboard | Panels | Datasource(s) | Estado |
|---|---|---|---|
| GPU AI Metrics | 30 | Prometheus | ✅ |
| Cognitive Runtime Core | 19 | Prometheus | ✅ |
| Energy / Thermal Operations | 18 | Prometheus | ✅ |
| Event Bus | 16 | Prometheus | ✅ |
| AI Governance | 16 | Prometheus + Infinity | ✅ |
| Episodic Memory | 15 | Prometheus + Infinity | ✅ |
| AI-LAB Runtime — ubuntu-ialab | 14 | Prometheus | ✅ |
| AI Sessions | 13 | Prometheus + Infinity | ✅ |
| Cluster Topology | 11 | Prometheus + Infinity | ✅ |

**Total: 9 dashboards, 152 paneles funcionales**

### Métricas GPU en vivo

| Métrica | RX9070 | RX7900XT |
|---|---|---|
| GPU Core Temp | 51°C | 29°C |
| GPU Memory Temp | 72°C | 54°C |
| Hot Spot | 53°C | 34°C |
| VRAM Total | 16304 MB | 20464 MB |
| VRAM Used | 15452 MB | 19940 MB |
| VRAM Free | 852 MB | 524 MB |
| GPU Package Power | 51 W | 57 W |
| GPU Memory Clock | 2505 MHz | — |
| D3D Load (3D) | 0% | 0% |

### APIs del runtime verificadas

| Endpoint | Ruta | Status |
|---|---|---|
| Analytics | `GET /api/analytics` | ✅ 200 |
| Watchdog | `GET /api/watchdog` | ✅ 200 |
| Model Performance | `GET /api/model-performance` | ✅ 200 |
| Learning Patterns | `GET /api/learning/patterns` | ✅ 200 |

## Resumen operativo

| Sistema | Estado |
|---|---|
| Servicios systemd (router, live-api, heartbeat) | ✅ Todos running |
| Puertos API (8083, 8084, 8008, 4322) | ✅ Todos respondiendo |
| Prometheus targets | ✅ 14/14 UP |
| Grafana dashboards AI-LAB | ✅ 9/9 con datos |
| GPUs (RX9070, RX7900XT) | ✅ Métricas D3D completas |
| FASE 12 learning engine | ✅ Ciclo completo operativo |

## Commit

```
31421a3 docs: informe completo sesion telemetria GPU + disciplina prompting
980e5d9 fix: pre-commit restart ailab-docs service after build
```
