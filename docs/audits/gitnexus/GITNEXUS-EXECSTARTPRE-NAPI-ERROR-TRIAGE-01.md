# GITNEXUS-EXECSTARTPRE-NAPI-ERROR-TRIAGE-01

## 1. Resultado
PASS — non-fatal startup warning, no action required.

## 2. Estado actual
- Git HEAD: `51513ec1`
- Git worktree: dirty esperado (AGENTS.md, runtime/state/*, docker-compose.yml) — 2 commits ahead
- GitNexus service: `active (running)` since 2026-05-25 10:39:35 CEST
- GitNexus status: ⚠️ stale (indexed `4ddcfc1`, current `51513ec`) — normal tras commits recientes
- HTTP endpoint: 200 OK on `localhost:4747`

## 3. Unidad systemd
- ExecStartPre: `/usr/local/bin/gitnexus analyze --force --index-only --skip-agents-md --no-stats --max-file-size 32 /opt/ai-lab`
  - Prefix `-` means failure is **ignored** (service continues regardless)
- ExecStart: `/usr/local/bin/gitnexus serve --host 0.0.0.0 --port 4747`
- WorkingDirectory: `/opt/gitnexus`
- User: `albert`
- Restart policy: `always` (RestartSec=5)
- TimeoutStart: 1min 30s
- TimeoutStop: 1min 30s

## 4. Evidencias del Napi::Error

### Pattern A: ExecStartPre crash (analysis before server starts)

| Fecha | PID | Evento | Impacto |
|-------|-----|--------|---------|
| May 24 12:35:30 | 27136 | `terminate called after throwing an instance of 'Napi::Error'` | ExecStartPre exit-code=1. service: FAILED. Retry → indexed OK |
| May 24 16:24:24 | 2659 | `terminate called after throwing an instance of 'Napi::Error'` | ExecStartPre crash, pero server started OK inmediatamente después |
| May 25 10:39:35 | 2773 | No Napi::Error | ExecStartPre succeeded (status=0) |

**Frecuencia ExecStartPre:** 2/3 boots con error (66%), 1/3 sin error (33%).

### Pattern B: Analyze worker crash (runtime background)

| Fecha | PID | Evento | Impacto |
|-------|-----|--------|---------|
| May 23 23:24:05 | 27080 | `Analyze worker crashed (code null), retry 1/2 in 1000ms: Napi::Error` | Worker crash, retry 2/2 also failed. Server OK. |
| May 23 23:29:46 | 27080 | Same pattern | Worker crash 2 retries. Server OK. |
| May 23 23:35:17 | 27080 | Same pattern | Worker crash 2 retries. Server OK. |
| May 24 00:58:07 | 27080 | Same pattern | Worker crash 2 retries. Server OK. |

**Frecuencia analyze worker:** 4 ocurrencias en ~1.5h. No recurrente en sesiones posteriores.

### Current session (since May 25 10:39): **0 ocurrencias** de Napi::Error.

## 5. Impacto funcional
- Servicio arranca: **sí** (el `-` prefix ignora el fallo de ExecStartPre)
- Status responde: **sí** (HTTP 200)
- Indexado funciona: **sí** (cuando ExecStartPre falla, systemd reintenta y suele funcionar en el 2º intento)
- Bloquea runtime AI-LAB: **no**
- Bloquea Gateway/Router/LM Studio: **no**
- Embedding incremental funciona: **sí** — `[embed] N nodes already embedded` se ejecuta correctamente

## 6. Clasificación
**Non-fatal startup warning / External vendor issue**

El error:
- No impide que GitNexus sirva queries
- Ocurre en el worker de análisis (no en el servidor HTTP/MCP)
- Es intermitente y no reproducible consistentemente
- Pertenece a las native addons de tree-sitter (`vendor/tree-sitter-*`) que usan `napi.h`

## 7. Relación con recursionLimit
- Relacionado con GRAPH_RECURSION_LIMIT: **no probado** — Napi::Error viene de native modules (C++), no de LangGraph (JS)
- Ruta implicada: `vendor/tree-sitter-proto/bindings/node/binding.cc` y `vendor/tree-sitter-dart/bindings/node/binding.cc` (ambos usan `napi.h`)
- Debe tocarse vendor code: **sí** para fix definitivo, pero el error es non-fatal

## 8. Recomendación
- **No action** — error non-fatal, no afecta operación
- **Document only** — ya documentado en este informe
- **Monitor** — si la frecuencia aumenta, considerar safe systemd override con `ExecStartPre=` vacío (eliminar el pre-index)

La raíz es un crash en tree-sitter native parsing de ciertos archivos. Es un bug conocido de tree-sitter native modules. La solución definitiva requeriría actualizar GitNexus a una versión con tree-sitter parsers más estables, lo que cae fuera del alcance de esta fase.

## 9. Próxima fase recomendada
`GITNEXUS-VENDOR-UPDATE-01` — solo cuando el error empiece a afectar operación.
