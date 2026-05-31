---
title: "FASE 29.4.3 — Runtime Identity Grounding Fix"
summary: "Corrige el problema de identidad runtime: hostname ubuntu-ialab y IP 192.168.1.30 son la misma entidad. El runtime ahora conoce explícitamente primary_runtime_ip, runtime_identity y target_runtime_match, eliminando falsas negaciones 'AI-LAB no está levantado en 192.168.1.30'."
order: 81
---

## Problema

El runtime conocía `hostname` pero NO lo vinculaba explícitamente con la IP principal:

- `hostname` = ubuntu-ialab
- IP principal = 192.168.1.30

El modelo interpretaba: "hostname conocido pero IP no confirmada", respondiendo:

> "AI-LAB no está levantado en 192.168.1.30"

cuando 192.168.1.30 ES el runtime principal.

## Cambios

### Modificado: `runtime/context/report_runtime_context.py`

Añadidos campos explícitos de identidad runtime:

```python
PRIMARY_RUNTIME_IP = "192.168.1.30"
RUNTIME_HOSTNAME = "ubuntu-ialab"
INFERENCE_BACKEND_IPS = frozenset({"192.168.1.50"})
INVENTORY_IPS = frozenset({"192.168.1.60"})
```

Nuevas funciones:

- `runtime_identity()` — devuelve `runtime_identity`, `runtime_hostname`, `primary_runtime_ip`, `primary_runtime_role`
- `classify_target_role(ip_or_host)` — clasifica target en `primary-control-plane` / `inference-backend-gpu` / `inventory-offline` / `unknown`
- `_resolve_hostname(host)` — resuelve hostname a IP vía DNS

`build_report_runtime_context(target_ip=None)` ahora acepta `target_ip` opcional. Cuando se provee, añade:

| Campo | Descripción |
|-------|-------------|
| `target_runtime_ip` | IP/hostname solicitado |
| `target_runtime_role` | Rol clasificado |
| `target_runtime_match` | True si coincide con runtime principal |

Ejemplo de salida OBSERVED_RUNTIME para informe sobre 192.168.1.30:

```json
{
  "runtime_identity": "ubuntu-ialab@192.168.1.30",
  "runtime_hostname": "ubuntu-ialab",
  "primary_runtime_ip": "192.168.1.30",
  "primary_runtime_role": "primary-control-plane",
  "target_runtime_ip": "192.168.1.30",
  "target_runtime_role": "primary-control-plane",
  "target_runtime_match": true
}
```

### Modificado: `runtime/gateway/openai_gateway.py`

Se cambió el orden de ejecución para pasar `target_ip` a `format_report_runtime_context`:

```python
_report_grounded_target = extract_target_ip(user_text)
_report_runtime = format_report_runtime_context(target_ip=_report_grounded_target)
```

Se añadieron métricas de identity match/mismatch:

```python
if _ctx.get("target_runtime_match"):
    REPORT_RUNTIME_IDENTITY_MATCH.inc()
elif _ctx.get("target_runtime_ip"):
    REPORT_RUNTIME_IDENTITY_MISMATCH.inc()
```

### Modificado: `runtime/prompts/report_prompt.md`

Añadidas reglas explícitas de identidad runtime:

- Si `primary_runtime_ip` coincide con IP solicitada: NO negar identidad, NO decir "no hay información"
- Si `target_runtime_match` es True: el target ES el runtime principal
- `ubuntu-ialab` y `192.168.1.30` son la misma entidad
- Nodos GPU son backends, no identidad principal

### Modificado: `runtime/telemetry/prometheus_metrics.py`

Nuevas métricas:

- `ailab_report_runtime_identity_match_total` — target coincide con runtime principal
- `ailab_report_runtime_identity_mismatch_total` — target NO coincide

### Nuevo: `tests/test_runtime_identity_grounding_29_4_3.py`

Tests que cubren:

- IP matching (1.30 → match, 1.50 → no match, 1.60 → no match)
- Hostname binding (ubuntu-ialab → match)
- Backend classification (1.50 → inference-backend-gpu)
- Inventory classification (1.60 → inventory-offline)
- Runtime classification (1.30 → primary-control-plane)
- No false denial (runtime nunca dice "no hay información" para 1.30)
- Role separation (control-plane ≠ backend ≠ inventory)
- `format_report_runtime_context` con y sin target_ip

## Arquitectura de identidad

### Runtime Identity Model

```
ubuntu-ialab@192.168.1.30
  ├─ primary_runtime_ip: 192.168.1.30
  ├─ runtime_hostname: ubuntu-ialab
  └─ role: primary-control-plane
```

### Control-Plane vs Backend Distinction

| Rol | IP | Descripción |
|-----|----|-------------|
| `primary-control-plane` | 192.168.1.30 | Runtime principal: gateway, router, live-api |
| `inference-backend-gpu` | 192.168.1.50 | Backend GPU RX9070: llama.cpp, 16GB VRAM |
| `inventory-offline` | 192.168.1.60 | Nodo RX7900XT: apagado, inventariado |

### IP Grounding Logic

```
extract_target_ip(user_text)
  → classify_target_role(ip_or_host)
    → if IP matches primary: target_runtime_match = True
    → if IP matches inference: role = inference-backend-gpu
    → if IP matches inventory: role = inventory-offline
    → else: role = unknown
```

## Validación

| Test | Input | Esperado |
|------|-------|----------|
| TEST 1 | "informe de ai-lab en 192.168.1.30" | Reconoce runtime principal |
| TEST 2 | "informe de 192.168.1.50" | Describe RX9070 backend |
| TEST 3 | "informe de 192.168.1.60" | Inventory/offline |
| TEST 4 | "informe de ubuntu-ialab" | Hostname → match con IP principal |

El runtime NUNCA debe responder "no hay información de 192.168.1.30".
