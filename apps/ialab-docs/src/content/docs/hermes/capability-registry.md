---
title: "Capability Registry"
summary: "6 capabilities críticas con dependencias, governance levels y validación cruzada."
order: 4
---

## Estado: ✅ Implementado

## Capacidades

| ID | Nombre | Dependencias | MCP Requerido |
|----|--------|-------------|---------------|
| `ai-lab-runtime` | AI-LAB Runtime | — | `ailab-runtime-mcp`, `gitnexus` |
| `marketplace-operator` | Marketplace Operator | `gitnexus-analysis` | `gitnexus`, `marketplace-mcp` |
| `observability` | Observability | — | — (no directo) |
| `gitnexus-analysis` | GitNexus Analysis | — | `gitnexus` |
| `deployment-review` | Deployment Review | `ai-lab-runtime`, `gitnexus-analysis` | `gitnexus`, `ailab-runtime-mcp` |
| `incident-response` | Incident Response | `ai-lab-runtime`, `observability` | `ailab-runtime-mcp`, `gitnexus` |

## Grafo de dependencias

```
ai-lab-runtime (raíz)
├── observability
│   └── incident-response
└── gitnexus-analysis
    ├── marketplace-operator
    └── deployment-review
```

**Sin ciclos.** Grafo acíclico validado.

## Governance Levels

Cada capability tiene en su `permissions.governance_levels` su comportamiento por modo:

| Capability | NORMAL | ELEVATED | DEGRADED | LOCKDOWN |
|------------|--------|----------|----------|----------|
| ai-lab-runtime | allowed | requires_approval | allowed | allowed |
| marketplace-operator | allowed | allowed | blocked | blocked |
| observability | allowed | allowed | allowed | blocked |
| gitnexus-analysis | allowed | allowed | allowed | blocked |
| deployment-review | requires_approval | requires_approval | blocked | blocked |
| incident-response | allowed | allowed | allowed | allowed |

## Validación

- 24 tests específicos en `test_hermes_capability_registry.py`
- IDs únicos, campos requeridos, dependencias existentes
- Sin ciclos en el grafo
- Critical capabilities (6) presentes
- MCP referenciados existen en MCP Registry
