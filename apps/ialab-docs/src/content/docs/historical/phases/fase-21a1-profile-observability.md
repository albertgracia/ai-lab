---
title: "FASE 21A.1 — Observabilidad de Perfiles Cognitivos"
summary: "Trazabilidad completa del perfil cognitivo aplicado a cada peticion: stdout, audit y Prometheus con labels profile, route_family y model."
order: 45
---

## Hito

Se completo la capa de observabilidad de perfiles cognitivos. Cada peticion ahora deja traza en 3 canales simultaneos.

## Canales

| Canal | Ubicacion | Formato | Uso |
|-------|----------|---------|-----|
| **stdout** | `journalctl -u ailab-gateway -f` | `profile=chat v=21.1 route=cognitive model=qwen2.5-14b tokens=16 temp=0 tools=False source=profile_loader` | Debug en tiempo real |
| **Audit** | `/opt/ai-lab/runtime/state/governance_audit.jsonl` | `audit_event("profile_applied", {...})` | Historico persistente |
| **Prometheus** | `http://127.0.0.1:8008/metrics` | `ailab_profile_total{profile,route_family,model}` | Dashboard y alertas |

## Metadatos inyectados

Cada payload recibe ahora:

- `_profile` = nombre del perfil (`"chat"`, `"observe"`, etc.)
- `_profile_version` = version (`"21.1"`)
- `_profile_source` = origen (`"profile_loader"` o `"legacy_fallback"`)

## Metrica Prometheus

```promql
ailab_profile_total{profile="chat",route_family="cognitive",model="qwen2.5-coder-14b-instruct"}
```

Labels: `profile`, `route_family`, `model`.

Para Grafana:

```promql
sum by (profile) (rate(ailab_profile_total[5m]))
```

## Como verificar

```bash
# Log en tiempo real
journalctl -u ailab-gateway -f | grep "profile="

# Audit
tail -f /opt/ai-lab/runtime/state/governance_audit.jsonl | grep profile_applied

# Prometheus
curl -sS http://127.0.0.1:8008/metrics | grep ailab_profile_total
```

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase21a-backup/prometheus_metrics.py /opt/ai-lab/runtime/telemetry/
cp /opt/ai-lab/snapshots/fase21a-backup/router_api.py /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase21a-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 21B — De-hardcoding progresivo de parametros duplicados con el profile_loader.
