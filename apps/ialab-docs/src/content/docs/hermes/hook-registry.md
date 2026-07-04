---
title: "Hook Registry"
summary: "9 lifecycle hooks para eventos del pipeline Hermes. Todos disabled."
order: 6
---

## Estado: ⚠️ Skeleton

## Lifecycle Hooks

| Hook | Evento | Enabled | Mode |
|------|--------|---------|------|
| `pre-operator-dispatch` | pre_operator | false | declarative_only |
| `post-operator-execution` | post_operator | false | declarative_only |
| `pre-gitnexus-analysis` | pre_execution | false | declarative_only |
| `post-gitnexus-analysis` | post_execution | false | declarative_only |
| `pre-governance-transition` | pre_governance | false | declarative_only |
| `post-governance-transition` | post_governance | false | declarative_only |
| `pre-incident-response` | pre_incident | false | declarative_only |
| `pre-marketplace-audit` | pre_marketplace | false | declarative_only |
| `post-marketplace-audit` | post_marketplace | false | declarative_only |

## Características

- **9 hooks**: cubren eventos pre/post en operators, gitnexus, governance, incidentes y marketplace.
- **Enforcement desactivado**: `enabled: false` en todos.
- **Modo declarativo**: `mode: declarative_only` — el runtime no ejecuta hooks.
- **Timeout configurable**: 5000ms por defecto.
- **Failure policy**: `log` — fallos silenciosos.

## Planificado

La activación de hooks está planificada para fases posteriores (E08+):
1. Hooks de logging (solo observación)
2. Hooks de validación (pre-ejecución)
3. Hooks de enforcement (post-estabilización)
