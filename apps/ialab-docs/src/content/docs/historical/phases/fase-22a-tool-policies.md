---
title: "FASE 22A — Tool Runtime Policies"
summary: "Politicas de herramientas declarativas en runtime/policies/tools/. Tres modos (disabled/readonly/agentic), lista maestra global de bloqueo, filtrado por allowed/blocked names."
order: 46
---

## Hito

Se completo la capa de politicas de herramientas del AI-LAB. Las reglas de tools salen del codigo y se vuelven declarativas en `runtime/policies/tools/`.

## Arquitectura

```
runtime/policies/tools/
├── blocked_tools.json       # Lista maestra global (nunca se sobreescribe)
├── manifest_tools.json      # Mapeo perfil -> politica
├── disabled_policy.json     # Sin tools (rutas ligeras)
├── readonly_policy.json     # Solo lectura (coding)
├── agent_policy.json        # Tools completas con confirmacion
└── policy_loader.py         # Loader con apply_tool_policy()
```

## Modos

| Modo | Comportamiento | Uso |
|------|---------------|-----|
| **disabled** | Todas las tools eliminadas | minimal, casual, greeting, observe, chat, analysis |
| **readonly** | Solo herramientas en `allowed_names` | coding |
| **agentic** | Tools preservadas (solo master bloqueadas) | tool_use, tool_fastpath |

## Jerarquia de decision

```
blocked_tools.json (GLOBAL MASTER)
  -> politica.blocked_names (override por perfil)
    -> politica.allowed_names (filtro positivo)
      -> guard hardcoded (tool_call_is_dangerous, qwen2.5 pop)
```

## Integracion

Un solo punto de inyeccion: `apply_profile()` en `profile_loader.py`. No se toco `router_api.py` ni `openai_gateway.py`.

Se mantiene `"tools": {"allowed": false}` en los perfiles como fallback legacy.

## Guards preservados

| Guard | Motivo |
|-------|--------|
| `_DANGEROUS_COMMAND_MARKERS` | Circuit breaker global |
| `tool_call_is_dangerous()` | Validacion post-respuesta |
| `GOVERNANCE_BLOCKED` | Metrica de seguridad |
| `qwen2.5-coder-14b` pop tools | Proteccion de modelo |

## Metadatos

Cada payload recibe:
- `_tool_policy` = nombre de la politica (`"disabled"`, `"readonly"`, `"agent"`)
- `_tool_mode` = modo (`"disabled"`, `"readonly"`, `"agentic"`)
- `_tool_source` = `"manifest_tools"`

## Validacion

| Ruta | Modo | Resultado |
|------|------|-----------|
| minimal con tools | disabled | tools eliminadas |
| general con tools | disabled | tools eliminadas |
| casual con tools | disabled | tools eliminadas |
| coding con read+bash+write | readonly | solo read preservada |
| agent con bash+read+write | agentic | todas preservadas (master none blocked) |

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase22a-backup/profile_loader.py /opt/ai-lab/runtime/profiles/
sudo systemctl restart ailab-router ailab-gateway
```

## Siguiente fase

FASE 22B — Shell sandboxing, bash_allowed_commands, parsing de comandos y ejecucion segura.
