# GITNEXUS-AILAB-REINDEX-SYNC-03

**Estado:** PARTIAL
**Fecha:** 2026-07-04
**Entorno:** Windows local (E:\opencode\ai-lab)

---

## 1. Local reindex (completado)

| Parámetro | Valor |
|-----------|-------|
| HEAD | `ff68d78` — `feat(hermes): E04A hook registry skeleton` |
| Nodes | **20,327** |
| Edges | **32,455** |
| Clusters | **528** |
| Flows | **300** |
| Heres files indexados | `runtime/hermes/` con estructuras SOUL, Capability, Operator, Hook y schemas |

### Validación local

```
query("runtime/hermes/hooks")      → ✅ procesos y símbolos encontrados
context("HermesHookRegistry")      → ✅ presente en índice
impact("load_hook_registry", ...)  → ✅ upstream/downstream funcional
```

## 2. Server .30 (no reindexado)

| Parámetro | Valor |
|-----------|-------|
| Servidor | 192.168.1.30 (Ubuntu) |
| `list_repos` | `ai-lab` en `/opt/ai-lab` — índice del servidor |
| Drift | **19 commits behind HEAD** (desde `0f5e3ab8`) |
| MCP `list_repos` | Sigue viendo índice antiguo (no refleja E01A-E04A) |

**El server-side index NO se actualizó** porque no hubo acceso SSH desde este entorno Windows.

## 3. Impacto del staleness

| Consecuencia | Severidad |
|-------------|-----------|
| MCP tools (impact, context, query) devuelven datos desactualizados | ALTA |
| DRIFT-HIGH del E01B-SOUL-VALIDATION no queda cerrado | ALTA |
| Hermes no puede consultar GitNexus contra runtime real | MEDIA |
| Desarrollo local sí tiene índice fresco (Windows) | BAJA (local OK) |

## 4. Acción pendiente manual

Ejecutar en el servidor .30 cuando haya acceso:

```bash
cd /opt/ai-lab
# 1. Verificar estado
git status --short
git rev-parse HEAD

# 2. Reindexar
npx gitnexus analyze --force --max-file-size 2048

# 3. Verificar resultado
npx gitnexus list-repos
npx gitnexus query "runtime/hermes/hooks"

# 4. Validar desde MCP (otro cliente)
# ailab-runtime-mcp → list_mcp_resources → debe reflejar nuevo índice
```

## 5. Conclusión

**PARTIAL.** Reindex local completado, pero el DRIFT-HIGH del server-side GitNexus .30 sigue abierto. No se cierra PASS hasta que se reindexe el servidor y se valide con MCP.
