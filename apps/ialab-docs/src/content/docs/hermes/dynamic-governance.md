---
title: "Dynamic Governance"
summary: "4 modos de governance (NORMAL, ELEVATED, DEGRADED, LOCKDOWN) con resolver de señales, anti-flapping y matrix de capabilities."
order: 8
---

## Estado: ✅ Implementado

**Enforcement:** ❌ Desactivado

## Modos de governance

| Modo | Descripción | Default Capability |
|------|-------------|-------------------|
| **NORMAL** | Capacidad operacional completa | `read_only` |
| **ELEVATED** | Escrutinio aumentado | `requires_approval` |
| **DEGRADED** | Capacidad reducida, solo observación crítica | `blocked_except_observe` |
| **LOCKDOWN** | Emergencia, solo health checks e incident reporting | `blocked` |

## Resolver

El `GovernanceResolver` traduce señales del runtime a modo de governance:

| Señal | Condición → Modo |
|-------|-----------------|
| `emergency_mode=true` | → LOCKDOWN |
| `degradation_level=HEAVY/EMERGENCY` | → DEGRADED |
| `degradation_level=LIGHT` | → ELEVATED |
| `slo_state=RED` | → ELEVATED |
| `vram_pressure>0.9` | → ELEVATED |
| `gpu_pressure>0.9` | → ELEVATED |
| `timeout_rate>0.1` | → ELEVATED |
| Default | → NORMAL |

**Prioridad:** LOCKDOWN > DEGRADED > ELEVATED > NORMAL

## Anti-flapping

- Mínimo **30 segundos** entre transiciones.
- Transiciones estabilizadas requieren períodos de cooling:
  - ELEVATED → NORMAL: 60s estable
  - DEGRADED → NORMAL: 120s estable
  - LOCKDOWN → cualquier modo: solo manual

## Capability-Governance Matrix

| Capability | NORMAL | ELEVATED | DEGRADED | LOCKDOWN |
|------------|--------|----------|----------|----------|
| ai-lab-runtime | allowed | requires_approval | allowed | allowed |
| marketplace-operator | allowed | allowed | **blocked** | **blocked** |
| observability | allowed | allowed | allowed | **blocked** |
| gitnexus-analysis | allowed | allowed | allowed | **blocked** |
| deployment-review | **requires_approval** | **requires_approval** | **blocked** | **blocked** |
| incident-response | allowed | allowed | allowed | allowed |

## Estado de enforcement

```json
{
  "governance": {
    "mode": "NORMAL",
    "enforcement_active": false,
    "anti_flapping": true,
    "modes": ["NORMAL", "ELEVATED", "DEGRADED", "LOCKDOWN"]
  }
}
```

## Reglas de transición

| Desde → Hasta | Permitido | Cooling |
|---------------|-----------|---------|
| NORMAL → ELEVATED/DEGRADED/LOCKDOWN | ✅ Inmediato | 0s |
| ELEVATED → NORMAL | ✅ | 60s estable |
| ELEVATED → DEGRADED/LOCKDOWN | ✅ Inmediato | 0s |
| DEGRADED → NORMAL | ✅ | 120s estable |
| DEGRADED → ELEVATED/LOCKDOWN | ✅ Inmediato | 0s |
| LOCKDOWN → cualquier | ❌ Solo manual | — |

## Referencia

- Implementación: `runtime/hermes/governance/resolver.py`
- Modos: `runtime/hermes/governance/modes.json`
- Matrix: `runtime/hermes/governance/matrix.json`
