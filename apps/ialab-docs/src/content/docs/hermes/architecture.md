---
title: "Architecture"
summary: "Arquitectura de Hermes Enterprise: gimnasia relacional entre SOUL, capabilities, operators, hooks, MCP y governance."
order: 2
---

## Visión general

Hermes Enterprise organiza el runtime en 6 capas registradas más un endpoint de observabilidad. Cada capa tiene una responsabilidad específica y un contrato formal.

## Gimnasia relacional

```
SOUL (identity) → Capability (what) → Operator (how) → Hook (when/event) → MCP (where/tools)
                                                                                │
                                                                                ▼
                                                                      Dynamic Governance (policy)
                                                                                │
                                                                                ▼
                                                                      Status Endpoint (observability)
```

## Flujo de datos

1. **SOUL** define la identidad, el truth model y los protocolos del agente.
2. **Capabilities** declaran qué dominios puede operar el sistema y qué MCP necesita.
3. **Operators** asignan execution modes y contratos a cada capability.
4. **Hooks** definen eventos lifecycle en puntos del pipeline.
5. **MCP** expone herramientas read-only para el acceso a datos.
6. **Governance** resuelve el modo dinámico basado en señales runtime.
7. **Status Endpoint** expone todo el estado como JSON.

## Ubicación en el código

```
runtime/hermes/
├── soul/              → SOUL YAML (5 archivos)
├── capabilities/      → Capability YAML (6 archivos + schema JSON)
├── operators/         → Operator YAML (5 archivos)
├── hooks/             → Hook YAML (9 archivos + registry)
├── mcp/               → MCP YAML (5 archivos + registry + schema)
├── governance/        → Governance JSON (modes, matrix, schema + resolver)
├── loader.py          → Carga read-only de todos los registros
├── models.py          → Dataclasses de todos los componentes
├── validation.py      → Validación cruzada entre registros
├── status.py          → Status JSON base
├── enterprise_status.py → Status JSON enriquecido (git, architecture, sections)
├── endpoint.py        → Servidor HTTP GET /hermes/status
└── __init__.py        → Export público
```

## Principios de diseño

- **Declarativo**: todos los registros son YAML/JSON, no código Python.
- **Validación automática**: el loader valida referencias cruzadas al cargar.
- **Zero enforcement**: enforcement_active=false, hooks disabled.
- **Read-only**: el loader nunca modifica archivos ni runtime.
- **Versionado**: cada registro tiene `version` semántica.
