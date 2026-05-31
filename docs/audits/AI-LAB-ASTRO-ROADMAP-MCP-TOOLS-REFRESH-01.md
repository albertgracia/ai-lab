# AI-LAB-ASTRO-ROADMAP-MCP-TOOLS-REFRESH-01

**Fecha:** 2026-05-31
**Modo:** SAFE APPLY
**Resultado:** PASS

---

## 1. Base

| Campo | Valor |
|-------|-------|
| HEAD base | `b39343fc` |
| Rama | `main` |
| Working tree pre-change | limpio |
| Push | no realizado |
| Tag | no creado |

## 2. Archivo actualizado

| Archivo | Uso |
|---------|-----|
| `apps/ialab-docs/src/pages/ai-infrastructure/index.astro` | Página `/ai-infrastructure` actualizada |

## 3. Ruta validada

| Ruta | Estado |
|------|--------|
| `/ai-infrastructure` | ✅ válida |
| `/infra` | referencia ligera desde la página |

## 4. Roadmap actualizado

### Bloques recientes conservados/resumidos

- Astro docs consolidation
- `/infra` Infrastructure Inventory refresh
- Grounding UNKNOWN_STATE_TOKENS fix
- Prometheus rules sync validation
- Observability `.40` disk cleanup

### Pendiente

- `AILAB_MCP_TOKEN` + LAN controlled mode
- Tools semánticas reales: `sommelier`, `analyze_label`, `price_estimate`
- Diagnóstico `ailab-router/auto`
- Rioja Marketplace integration
- Multi-GPU runtime scheduler
- Hyper-V checkpoint (operator action)

## 5. MCP Tools

### Confirmadas

| Tool | Estado | Uso recomendado | Riesgo | Nota |
|---|---|---|---|---|
| `ailab_status` | confirmed | active | low | Estado resumido de gateway y router; read-only. |
| `ailab_runtime_health` | confirmed | active | low | Salud cognitiva/runtime detallada; read-only. |
| `ailab_route_preview` | confirmed | active | low | Clasificación heurística de rutas sin inferencia real. |

### En uso activo

- `ailab_status`
- `ailab_runtime_health`
- `ailab_route_preview`

### En preparación

- `sommelier`
- `analyze_label`
- `price_estimate`
- Rioja Marketplace integration

### En reserva / standby

- Tools mutables o destructivas
- Acciones que escriben estado/runtime
- Flujos que requieren aprobación del operador

### Pendiente de confirmar

- `runtime health tool` (nombre exacto no confirmado fuera de la documentación)

### Condiciones de activación

- `AILAB_MCP_TOKEN` definido
- `LAN controlled mode`
- allowlist de cliente
- logging auditable
- read-only por defecto
- aprobación del operador para acciones sensibles

## 6. Fuente y confirmación

| Fuente | Resultado |
|--------|-----------|
| `docs/runtime/mcp-semantic-gateway-01.md` | confirma 3 tools read-only |
| `docs/runtime/mcp-opencode-windows-connection-01.md` | confirma uso vía SSH tunnel y `AILAB_MCP_TOKEN` pendiente |
| `runtime/tools/tool_registry.py` | inventario conservador de tools runtime, no expuesto como MCP público confirmado |

## 7. Build y validación

| Prueba | Resultado |
|--------|-----------|
| `npm run build` | PASS |
| Páginas generadas | 258 |
| Errores | 0 |
| `dist/ai-infrastructure/index.html` | presente |

## 8. Validación de ruta

| Señal | Resultado |
|------|-----------|
| `Roadmap` / `Pendiente` | presente |
| `MCP Tools` | presente |
| `AILAB_MCP_TOKEN` | presente solo como nombre de variable |
| `sommelier`, `analyze_label`, `price_estimate` | presentes como roadmap |
| secretos / tokens reales | no detectados |

## 9. Confirmaciones operativas

| Aspecto | Estado |
|---------|--------|
| runtime/ tocado | no |
| servicios tocados | no |
| reinicios | no |
| Docker / systemd | no modificados |
| push | no |
| tag | no |

## 10. Riesgos residuales

| Riesgo | Severidad |
|--------|-----------|
| Algunas tools MCP quedan como pendiente de confirmar | baja |
| La activación LAN depende de `AILAB_MCP_TOKEN` y control de acceso | media |

## 11. Siguiente fase recomendada

**AI-LAB-RUNTIME-HEALTH-SCORE-SEMANTICS-AUDIT-01** o la siguiente fase de roadmap que alinee runtime health score semántico y NOC.

---

*Fin del informe AI-LAB-ASTRO-ROADMAP-MCP-TOOLS-REFRESH-01*
