---
title: "FASE 22B — Tool Execution Safety"
summary: "Sanitizador de comandos bash con token scanning, confirmation gate 428, auditoria por tool_call, presupuesto de tool_calls y metricas Prometheus por tool_name."
order: 47
---

## Hito

Se completo la capa de seguridad de ejecucion de herramientas del AI-LAB. Bash sanitizer con `shlex.split()`, gate de confirmacion para herramientas de escritura, auditoria por tool_call individual, presupuesto con metadatos y metricas Prometheus.

## Componentes

### Bash sanitizer (`runtime/policies/tools/bash_sanitizer.py`)

- Token scanning con `shlex.split()` (no regex)
- First token exact match, no `startswith()`
- Bloquea pipes, redirects, `&&`, `||`, `;`, `&`, subshells, `/dev/`
- `echo "foo|bar"` no se bloquea (la pipe esta entrecomillada)
- `ls | grep foo` se bloquea (pipe real)

### Confirmation gate (`openai_gateway.py`)

- **428 Precondition Required** (no 403)
- Solo para herramientas de escritura: `write`, `edit`, `rm`, `mv`, `cp`, `dd`, `tee`, `bash`
- Inyecta `_tool_confirmation_pending: true` para que OpenCode/OpenWebUI reaccionen

### Presupuesto de tool_calls

- `_tool_budget_original`: numero original de tools
- `_tool_budget_limit`: maximo permitido por politica
- `_tool_budget_exceeded`: True si se truncaron

### Auditoria por tool_call

Eventos en `governance_audit.jsonl`:
- `tool_call_allowed` → tool paso todos los filtros
- `tool_call_blocked_by_policy` → tool bloqueada (con motivo)

### Metricas Prometheus

```promql
ailab_tool_call_total{tool_name, result, policy, mode}
```

## Subfases

| Subfase | Commit | Riesgo |
|---------|--------|--------|
| 22B.1 | `feat: audit per tool_call` | Nulo |
| 22B.2 | `feat: tool call budget metadata` | Nulo |
| 22B.3 | `feat: bash sanitizer with shlex.split()` | Medio |
| 22B.4 | `feat: confirmation gate 428` | Alto |
| 22B.5 | `feat: TOOL_CALL_TOTAL metrics` | Nulo |

## Validacion

```bash
# Bash con pipe → bloqueado
curl :8008 -d '{"tools":[{"function":{"name":"bash","arguments":"ls | grep foo"}}]}'
# Expected: bash eliminada

# Bash sin pipe → OK
curl :8008 -d '{"tools":[{"function":{"name":"bash","arguments":"ls -la"}}]}'
# Expected: bash preservada

# Write tool → 428
curl :8008 -d '{"tools":[{"function":{"name":"write"}}],"messages":[{"role":"user","content":"ejecuta comando"}]}'
# Expected: 428 Precondition Required

# Metricas
curl :8008/metrics | grep ailab_tool_call_total
```

## Guards preservados

| Guard | Capa |
|-------|------|
| `_DANGEROUS_COMMAND_MARKERS` | Firewall post-respuesta |
| `tool_call_is_dangerous()` | Ultima linea de defensa |
| `GOVERNANCE_BLOCKED` | Metrica de seguridad |
| `qwen2.5-coder-14b` pop tools | Proteccion de modelo |

## Rollback

```bash
cp /opt/ai-lab/snapshots/fase22a-backup/policy_loader.py /opt/ai-lab/runtime/policies/tools/
cp /opt/ai-lab/snapshots/fase22a-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/
cp /opt/ai-lab/snapshots/fase22a-backup/prometheus_metrics.py /opt/ai-lab/runtime/telemetry/
sudo systemctl restart ailab-gateway
```

## Siguiente fase

FASE 22C — Sandbox real, seccomp, subprocess jail, rate limiting (`tool_calls_per_minute`).
