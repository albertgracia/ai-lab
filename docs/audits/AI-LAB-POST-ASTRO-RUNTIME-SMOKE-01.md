# AI-LAB-POST-ASTRO-RUNTIME-SMOKE-01

**Fecha:** 2026-05-31
**Modo:** READ-ONLY
**Resultado:** PASS (1 anomalía documentada)

---

## 1. Git Preflight

| Ítem | Resultado |
|------|-----------|
| Rama | `main` |
| HEAD local | `bbc71bb3` |
| Working tree | ✅ Limpio |
| Staged changes | ✅ Ninguno |
| Sincronización | ⚠️ **behind 1** — origin/main avanzó con `f386ac98 chore: update public metrics [skip ci]` |

**Nota:** El commit remoto es CI automático (`[skip ci]`), no humana. No requiere acción inmediata.

## 2. Systemd

| Ítem | Resultado |
|------|-----------|
| Unidades failed | ✅ **0** |
| Servicios AI-LAB activos | **10** (gateway, router, docs preview, heartbeat, live-api, live-state, mcp-semantic-gateway, metrics dashboard, runner, gitnexus) |

## 3. Docker

| Contenedor | Estado |
|------------|--------|
| qdrant | ✅ Up 3h |
| grafana | ✅ Up 3h (healthy) |
| prometheus (node-exporter) | ✅ Up 3h |
| promtail | ✅ Up 3h |
| open-webui | ✅ Up 3h (healthy) |
| traefik | ✅ Up 3h |
| portainer | ✅ Up 3h |
| +9 más (cadvisor, nginx sites) | ✅ Up 3h |

## 4. Health checks HTTP

| Endpoint | Puerto | Resultado |
|----------|--------|-----------|
| Gateway | 8008 `/health` | ✅ `{"status":"ok","service":"ai-lab-openai-gateway",...}` |
| Router | 8083 `/health` | ✅ `{"status":"ok","service":"ai-lab-router-api"}` |
| GitNexus | 4747 `/` | ✅ HTTP 200 (HTML page) |
| Qdrant | 6333 `/collections` | ✅ 8 colecciones |
| Astro Docs | 4322 `/` | ✅ HTTP 200 (26 KB) |

## 5. Métricas

| Endpoint | Métricas AI-LAB |
|----------|-----------------|
| Gateway 8008 `/metrics` | ✅ `ailab_requests_total`, `ailab_errors_total`, `ailab_latency`, `ailab_streams`, `ailab_routing_decisions`, `ailab_memory_*`, `ailab_sessions_*` |
| Router 8083 `/metrics` | ✅ `ailab_tool_calls_malformed_total`, Python GC metrics |

## 6. Astro Build

| Ítem | Resultado |
|------|-----------|
| Build | ✅ **PASS** |
| Páginas | **258** |
| Errores | **0** |

## 7. Astro Dist

| Ruta | Existe |
|------|--------|
| `dist/index.html` | ✅ (26 KB) |
| `dist/docs/audits/index.html` | ✅ (23 KB) |
| `dist/docs/codebase-structural-cognition/index.html` | ✅ (67 KB) |
| `dist/docs/historical/phases/index.html` | ✅ (25 KB) |

| Regresión | Resultado |
|-----------|-----------|
| Tokens Mermaid en HTML | ✅ **0** (limpio) |
| "Section titled" en sr-only span | ✅ Correcto (accesibilidad) |

## 8. Runtime Bugfix

| Prueba | Resultado |
|--------|-----------|
| `py_compile reporting_engine.py` | ✅ **PASS** |
| `pytest test_operational_reporting_31c.py` | ✅ **21/21 PASS** (1 warning: `datetime.utcnow()`) |

## 9. Confirmaciones

| Aspecto | Estado |
|---------|--------|
| Archivos modificados fuera del informe | ❌ No |
| Servicios reiniciados | ❌ No |
| Push realizado | ❌ No |
| Tag creado | ❌ No |
| Git add/commit prematuro | ❌ No |

## 10. Anomalía documentada

| ID | Descripción | Severidad | Acción |
|----|-------------|-----------|--------|
| S01 | Branch behind 1: origin/main avanzó con `f386ac98 chore: update public metrics [skip ci]` | **Baja** | CI automático. No requiere acción inmediata. Se sincronizará en la próxima fase que requiera push. |

## 11. Riesgos residuales

| Riesgo | Severidad |
|--------|-----------|
| Deprecation warning `datetime.utcnow()` en `runtime_state.py` | Baja |
| Branch behind 1 (CI commit) | Muy baja |

## 12. Siguiente fase recomendada

**AI-LAB-GIT-SYNC-CI-METRICS-01** (opcional) — Hacer `git pull --ff-only` para sincronizar el commit CI de métricas públicas, si se desea mantener el branch en sync.

---

*Fin del informe AI-LAB-POST-ASTRO-RUNTIME-SMOKE-01*
