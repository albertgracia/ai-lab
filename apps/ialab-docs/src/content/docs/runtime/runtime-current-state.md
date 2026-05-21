---
title: "Runtime Current State"
summary: "Estado actual real del runtime AI-LAB: control plane, observability, backends de inferencia, storage y checkpoints del baseline observacional."
order: 10
---

## Estado actual real

### Control plane

- Hostname: `ubuntu-ialab`
- IP principal: `192.168.1.30`
- Rol: `primary-control-plane`

### Observability

- Prometheus: `192.168.1.40:9090`
- Grafana: `192.168.1.40:3000`
- Los sensores del runtime se alimentan de Prometheus y del API de LM Studio.

### Inference backend activo

- GPU: `RX9070`
- Host: `192.168.1.50`
- Estado: `online`
- Fuente operativa: `Prometheus GPU exporter + LM Studio API`

### Inference backend inventariado

- GPU: `RX7900XT`
- Host: `192.168.1.60`
- Estado: `expected_offline / inventory`
- No activo
- No routable
- No debe generar métricas inventadas

### Storage

- Runtime vivo: `/opt/ai-lab`
- Runtime data: `/opt/ai-lab-data`
- Modelos: `/mnt/ai-models`
- Archives históricos: `/mnt/opencode/ai-lab-archives`

## Qué cambió con 30I

Antes:

```text
LLM + routing + prompts
```

Después:

```text
Runtime observacional cognitivo
→ Prometheus-backed evidence
→ Sensor fusion
→ Evidence-bound reporting
→ GPU operational summaries
→ source_of_truth / freshness / confidence
```

## Checkpoints relevantes

- `CP-30H-RUNTIME-EVIDENCE-ENFORCEMENT-STABLE`
- `CP-30H.1-UNIVERSAL-EVIDENCE-GUARD-STABLE`
- `CP-30H.2-RUNTIME-CONTEXT-INJECTION-STABLE`
- `CP-30I-RUNTIME-SENSOR-FUSION-STABLE`
- `CP-30I-B-SENSOR-FUSION-HARDENED-STABLE`
- `CP-30I-C-SENSOR-SUMMARY-EXPOSURE-STABLE`
- `CP-30I-D-SENSOR-SEMANTICS-NORMALIZED-STABLE`
- `CP-STORAGE-HARDENING-ARCHIVE-POLICY-STABLE`

## Límite explícito

Este estado es **pre-Multi-GPU**. RX7900XT sigue siendo inventario. No hay scheduler Multi-GPU documentado como implementado.
