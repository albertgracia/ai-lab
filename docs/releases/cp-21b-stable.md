# AI-LAB — Release CP-21B-STABLE

**Tag:** `CP-21B-STABLE`
**Fecha:** 2026-05-18
**Estado:** Producción (pre-release cognitivo)

---

## Hito

Primer release estable del AI-LAB con arquitectura gobernada por perfiles cognitivos. Se completó la migración al modelo principal `qwen/qwen2.5-coder-14b-instruct`, la limpieza de wrappers legacy y la normalización de prompts y comportamiento en capas separadas.

---

## Arquitectura

```
OpenCode / OpenWebUI / APIs
        ↓
AI-LAB Router (:8083)
        ↓
AI-LAB Gateway (:8008)
        ↓
LM Studio (:1234) → RX9070 (16 GB VRAM)
```

### Capas del runtime

```
runtime/
├── prompts/        → lenguaje (FASE 20C)
├── profiles/       → comportamiento (FASE 21A)
├── models/         → inferencia
├── llm/            → routing cognitivo
├── gateway/        → API OpenAI-compatible
├── memory/         → recall semántico
├── telemetry/      → métricas Prometheus
└── audit/          → trazabilidad
```

---

## Perfiles cognitivos

| Perfil | Modelo | max_tokens | temp | Tools | Memory | Reasoning |
|--------|--------|------------|------|-------|--------|-----------|
| **chat** | qwen2.5-coder-14b | 512 | 0.4 | NO | light | disabled |
| **coding** | qwen2.5-coder-14b | 1024 | 0.2 | NO | light | disabled |
| **analysis** | qwen2.5-coder-32b | 2048 | 0.3 | NO | full | enabled |
| **observe** | llama-3.1-8b | 256 | 0.1 | NO | minimal | disabled |
| **agent** | qwen3.6-27b | 2048 | 0.2 | SI | full | enabled |

### Overrides para rutas ligeras

`minimal`, `casual`, `greeting` y `report` usan `observe_profile.json` con `max_tokens: 96`.

---

## Modelos por ruta

| Ruta | Modelo |
|------|--------|
| `minimal/casual/greeting/report` | llama-3.1-8b-instruct |
| `observe` | llama-3.1-8b-instruct |
| `fast` | qwen/qwen2.5-coder-14b-instruct |
| `general/auto` | qwen/qwen2.5-coder-14b-instruct |
| `coding` | qwen/qwen2.5-coder-14b-instruct |
| `reasoning` | qwen2.5-coder-32b-instruct |
| `tool_use` | qwen/qwen3.6-27b |

---

## Métricas (Prometheus)

| Métrica | Labels | Descripción |
|---------|--------|-------------|
| `ailab_route_family_total` | `family` | Peticiones por ruta |
| `ailab_route_family_latency_ms` | `family` | Latencia por ruta |
| `ailab_profile_total` | `profile, route_family, model` | Peticiones por perfil |

### Observabilidad

3 canales simultáneos:
1. **stdout**: `journalctl -u ailab-gateway -f | grep "profile="`
2. **Audit**: `/opt/ai-lab/runtime/state/governance_audit.jsonl` → `profile_applied`
3. **Prometheus**: `:8008/metrics` → `ailab_profile_total`

---

## Rollback

```bash
# Rollback a FASE 21A (pre-dehardcoding)
git checkout 1e624506 -- runtime/llm/router_api.py runtime/gateway/openai_gateway.py
sudo systemctl restart ailab-router ailab-gateway

# Rollback total (pre-FASE 20)
git checkout 3296e271
sudo systemctl restart ailab-router ailab-gateway
```

---

## Riesgos abiertos

| Riesgo | Severidad | Mitigación |
|--------|-----------|-----------|
| Router directo (:8083) → 502 en algunas rutas | Media | Usar gateway (:8008) como entrypoint |
| qwen3.6-27b comportamiento errático con tools | Media | Usar solo para tool_use; FASE 22 añadirá políticas |
| LM Studio conexión persistente | Baja | `Connection: close` en router |
| max_tokens=2048 safety net en gateway | Baja | Mantenido como protección |

---

## Roadmap siguiente

| Fase | Descripción | Estado |
|------|-------------|--------|
| 20A | Migración modelo qwen2.5-14b | ✅ |
| 20B | Limpieza wrappers legacy | ✅ |
| 20C | Normalización prompts | ✅ |
| 21A | Perfiles cognitivos | ✅ |
| 21A.1 | Observabilidad perfiles | ✅ |
| 21B | De-hardcoding | ✅ |
| **22A** | Tool Runtime Policies | ⏭ |
| 22B | MCP tools controladas | ⏭ |
| 23 | Memoria semántica estable | ⏭ |
| 24 | Observabilidad cognitiva avanzada | ⏭ |
| 25 | Scheduler multi-GPU | ⏭ |
| 30 | AI-LAB v1.0 | ⏭ |

---

## Commits incluidos

```
7a523cdb refactor(fase21b-6): remove upstream setdefault(max_tokens/temperature) covered by profile_loader
f2b3dc38 refactor(fase21b-5): remove redundant pop(tools/tool_choice), model, temp in router observe/greeting
3202c871 refactor(fase21b-4): remove post-route temperature default covered by profile_loader
4426da5b refactor(fase21b-3): remove temperature/max_tokens coincident with profile_loader defaults
7e18cec7 refactor(fase21b-2): remove redundant model=llama assignments covered by profile_loader
1e624506 refactor(fase21b-1): remove redundant pop(tools/tool_choice) covered by profile_loader
0a61d531 feat(fase21a1): profile observability
0a61d531 feat(fase21a): cognitive profiles
55fe5d9e feat(fase20c): normalize runtime prompts
2a16528b feat(fase20b): clean legacy wrappers
6d8a6cac feat(fase20a): migrate router to qwen2.5-coder-14b
```
