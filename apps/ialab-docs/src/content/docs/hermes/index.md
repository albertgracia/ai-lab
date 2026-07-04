---
title: "Hermes Enterprise — Overview"
summary: "Hermes Enterprise es la capa de governance, registros y observabilidad declarativa del runtime AI-LAB. Define SOUL, capabilities, operators, hooks, MCP y governance dinámico."
order: 1
---

## Qué es Hermes Enterprise

Hermes Enterprise es el sistema de governance declarativo del runtime AI-LAB. Proporciona:

- **SOUL**: identidad, truth model, protocolos, boundaries y dominios del agente Hermes.
- **Capability Registry**: 6 capabilities críticas con dependencias y governance levels.
- **Operator Registry**: 5 operadores que ejecutan las capabilities con execution modes y truth model.
- **Hook Registry**: 9 lifecycle hooks para eventos del pipeline Hermes.
- **MCP Registry**: 5 servidores MCP declarativos para acceso a herramientas.
- **Dynamic Governance**: 4 modos de governance (NORMAL, ELEVATED, DEGRADED, LOCKDOWN) con resolver de señales y anti-flapping.
- **Runtime Status Endpoint**: `GET /hermes/status` como fuente oficial de observabilidad.

## Principios

1. **Declarativo primero**: todos los registros son YAML/JSON, cero enforcement por defecto.
2. **Validación cruzada**: capabilities→MCP, operators→capabilities, dependencias sin ciclos.
3. **Read-only**: el loader Python es puramente observacional; no modifica runtime.
4. **Zero enforcement inicial**: `enforcement_active=false`, hooks disabled, governance como resolver sin bloqueo activo.

## Estado actual

| Componente | Estado | Versión |
|------------|--------|---------|
| SOUL | ✅ Implementado | 1.0.0 |
| Capability Registry | ✅ Implementado | 1.0.0 |
| Operator Registry | ✅ Implementado | 1.0.0 |
| Hook Registry | ✅ Skeleton (disabled) | 1.0.0 |
| MCP Registry | ✅ Implementado | 1.0.0 |
| Dynamic Governance | ✅ Implementado | 1.0.0 |
| Status Endpoint | ✅ Implementado | 1.0.0 |

## Arquitectura

```
                    ┌──────────┐
                    │   SOUL   │
                    │ (identidad) │
                    └────┬─────┘
                         │
                         ▼
              ┌───────────────────┐
              │ Capability Registry │
              │    (what)          │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │ Operator Registry  │
              │    (how)          │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │   Hook Registry   │
              │   (when/event)    │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │ Dynamic Governance │
              │   (policy)        │
              └────────┬──────────┘
                       │
                       ▼
              ┌───────────────────┐
              │  Status Endpoint  │
              │ GET /hermes/status │
              └────────┬──────────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
       Astro Docs   Dashboard   Marketplace
```

## Separación de responsabilidades

| Capa | Rol | Formato |
|------|-----|---------|
| **SOUL** | Identidad y valores | `soul/*.yaml` |
| **Capability** | Qué puede hacer | `capabilities/*.yaml` |
| **Operator** | Cómo se hace | `operators/*.yaml` |
| **Hook** | Cuándo ocurre | `hooks/lifecycle/*.yaml` |
| **MCP** | Dónde/datos | `mcp/*.yaml` |
| **Governance** | Política y límites | `governance/*.json` |
| **Status** | Observabilidad | `GET /hermes/status` |

## Referencias

- [ADR-001: SOUL](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-001-SOUL.md)
- [ADR-002: Capability Registry](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-002-CAPABILITY-REGISTRY.md)
- [ADR-003: Operator Registry](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-003-OPERATOR-REGISTRY.md)
- [ADR-004: MCP Registry](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-004-MCP-REGISTRY.md)
- [ADR-005: Hook System](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-005-HOOK-SYSTEM.md)
- [ADR-006: Dynamic Governance](https://github.com/albertgracia/ai-lab/blob/main/docs/hermes/ADR-006-DYNAMIC-GOVERNANCE.md)
