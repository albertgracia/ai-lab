# AI-LAB-MCP-RUNTIME-METRICS-ROLLBACK-PUSH-01

## Resultado

PASS

## Objetivo

Publicar la documentación del rollback de métricas MCP y dejar constancia de que el runtime MCP LAN quedó recuperado.

## Commits publicados

- 84dda79f — docs(mcp): specify prometheus rules
- 70ae486b — docs(audit): document mcp metrics rollback

## Merge

- Merge commit: 46fcac02 — merge: integrate remote public metrics before mcp metrics rollback push
- 5 commits integrados de origin/main: chore: update public metrics [skip ci]
- Sin conflictos.

## Estado operativo tras rollback

El rollback del APPLY de métricas MCP fue ejecutado previamente usando:

- Backup: /home/albert/backups/ai-lab/mcp-runtime-apply/20260606-210855/mcp_server
- Rollback script: /tmp/rollback-mcp-runtime-metrics-apply.sh

Estado confirmado:

- 8091 /mcp: 406 Not Acceptable, esperado con curl simple.
- 8092 /mcp sin token: 401 Unauthorized, esperado.
- 8092 /mcp sin token + SSE: 401 Unauthorized, esperado.
- Sin timeouts en endpoints MCP.
- OpenCode: verde, confirmado por operador.
- LM Studio: OK, confirmado por operador.
- /metrics runtime: 404 Not Found — revertido tras rollback.

## Incidente documentado

El APPLY de métricas al runtime real causó una regresión en el gateway LAN 8092:

- GET /mcp con y sin Accept: text/event-stream llegó a timeout.
- Logs mostraron GET /mcp 404 desde 192.168.1.50.
- Logs mostraron warning ASGI callable returned without completing response.
- OpenCode quedó rojo.
- LM Studio quedó afectado.

## Decisión

- Prometheus implementation queda pausada.
- No continuar con AI-LAB-MCP-PROMETHEUS-RULES-IMPLEMENTATION-01 todavía.
- La siguiente fase debe ser repo-only/read-only de investigación:
  - AI-LAB-MCP-LAN-ASGI-404-TRIAGE-01

## Tests

`	ext
10 passed in 0.03s
`

## Secret scan

Limpio. Solo placeholders de test y referencias en documentación.

## Estado preservado en esta fase de push

| Aspecto | Estado |
|---|---|
| Sudo usado | No |
| Servicios reiniciados | No |
| /mnt/mcp_server modificado | No |
| mcp/runtime-mcp modificado | No |
| Token tocado | No |
| UFW/firewall tocado | No |
| Prometheus tocado | No |
| Grafana tocado | No |
| OpenCode tocado | No |
| LM Studio tocado | No |
| Docker tocado | No |
| Astro tocado | No |
| Reboot | No |
| Tag creado | No |

## Siguiente fase recomendada

AI-LAB-MCP-LAN-ASGI-404-TRIAGE-01
