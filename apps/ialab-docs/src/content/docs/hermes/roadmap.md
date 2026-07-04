---
title: "Roadmap"
summary: "Estado actual y planificación de Hermes Enterprise: implementado, skeleton y planificado."
order: 10
---

## ✅ IMPLEMENTADO

| FASE | Componente | Tests | Tags |
|------|------------|-------|------|
| E01A | SOUL Skeleton | — | `CP-E01A-SOUL-ENTERPRISE-SKELETON-STABLE` |
| E01B | SOUL Validation | — | — |
| E01C | Read-only Loader | 27 | `CP-E01C-SOUL-ENFORCEMENT-READONLY-LOADER-STABLE` |
| E02A | Capability Registry Skeleton | — | `CP-E02A-CAPABILITY-REGISTRY-SKELETON-STABLE` |
| E02B | Capability Registry Validator | 24 | `CP-E02B-CAPABILITY-REGISTRY-VALIDATOR-STABLE` |
| E03A | Operator Registry Skeleton | — | `CP-E03A-OPERATOR-REGISTRY-SKELETON-STABLE` |
| E02C | Operator Registry Validator | 17 | `CP-E02C-OPERATOR-REGISTRY-VALIDATOR-STABLE` |
| E04A | Hook Registry Skeleton | — | `CP-E04A-HOOK-REGISTRY-SKELETON-STABLE` |
| E05 | MCP Registry | — | `CP-E05-MCP-REGISTRY-SKELETON-STABLE` |
| E06 | Dynamic Governance | 45 | `CP-E06-DYNAMIC-GOVERNANCE-STABLE` |
| E07 | Runtime Status Endpoint | 72 | `CP-E07-ENTERPRISE-RUNTIME-STATUS-ENDPOINT-STABLE` |

**Total tests:** 185 PASS

## ⚠️ EXPERIMENTAL / SKELETON

| Componente | Motivo |
|------------|--------|
| Hook Registry | 9 hooks declarados pero todos disabled (`mode: declarative_only`) |
| MCP Prometheus | Servidor declarado como `planned`, sin implementación activa |
| MCP Marketplace | Servidor declarado como `planned`, sin implementación activa |

## 📋 PLANIFICADO

| FASE | Descripción | Prioridad |
|------|-------------|-----------|
| E08 | Hook runtime integration (primer lifecycle hook) | Alta |
| E09 | Governance enforcement (conectar resolver a runtime) | Alta |
| E10 | MCP execution runtime | Media |
| E11 | Operator dispatch runtime | Media |
| E12 | Enterprise telemetry | Baja |

## Notas

- **Enforcement**: desactivado globalmente (`enforcement_active=false`).
- **Hooks**: sin activación hasta E08.
- **Governance**: resuelve modo pero no bloquea operaciones.
- **MCP**: servidores `planned` no tienen tools operativas.
- **Operadores**: ningún operador en modo `execute`.
