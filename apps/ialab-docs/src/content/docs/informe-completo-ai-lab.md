---
title: "Informe Completo AI-LAB"
summary: "Inventario detallado de la VM, Astro, runtime, stacks y estado operativo actual del laboratorio."
order: 99
---

Informe de lectura del entorno AI-LAB, sin cambios aplicados.

## Resumen ejecutivo

AI-LAB vive en una VM Hyper-V con Ubuntu Server 26.04 LTS y combina:

- portal Astro para documentacion viva
- dashboard Next.js para metricas SSR
- runtime cognitivo en Python
- stacks Docker para proxy, observabilidad, Qdrant, Ollama y webs
- nodos GPU remotos con LM Studio

## Base del sistema

| Dato | Valor |
|---|---|
| Host | `ubuntu-ialab` |
| Virtualizacion | Microsoft Hyper-V |
| SO | Ubuntu 26.04 LTS |
| Kernel | `7.0.0-15-generic` |
| Arquitectura | `x86-64` |
| RAM | `7.2 GiB` |
| Swap | `4.0 GiB` |
| IP principal | `192.168.1.30` |

## Almacenamiento

| Punto de montaje | Tamano | Uso |
|---|---:|---:|
| `/` | `98.5G` | `78%` |
| `/mnt/ai-models` | `80G` | `4.4G` usados |
| `/opt/ai-lab-data` | `15G` | `153M` usados |
| `/mnt/opencode` | `3.8T` | share CIFS |

Capas pesadas dentro de `/opt/ai-lab`:

- `backups`: `16G`
- `snapshots`: `3.4G`
- `actions-runner`: `2.5G`
- `apps`: `1.4G`
- `stacks`: `779M`
- `runtime`: `30M`

## Red y puertos

| Puerto | Servicio |
|---|---|
| `22` | SSH |
| `80/443` | Traefik |
| `3000` | Open WebUI |
| `3010` | Metrics dashboard |
| `4322` | Astro docs preview |
| `4323/4324` | procesos Node adicionales |
| `8008` | AI-LAB gateway |
| `8083` | Router API |
| `8084` | Live API |
| `9000` | Portainer |
| `9100` | node-exporter |
| `11434` | Ollama |
| `6333/6334` | Qdrant |

## Servicios systemd

Servicios activos detectados:

- `ailab-docs`
- `ailab-gateway`
- `ailab-heartbeat`
- `ailab-live-api`
- `ailab-live-state`
- `ailab-metrics`
- `ailab-router`
- `ailab-runner`
- `ailab-traefik`
- `ialab-docs`
- `ialab-live-state`
- `ialab-router-api`

### Rol de los principales

| Servicio | Funcion |
|---|---|
| `ailab-gateway` | Gateway OpenAI-compatible |
| `ailab-router` / `ialab-router-api` | Router cognitivo capability-aware |
| `ailab-live-api` | Status, topology, analytics, recall, mode y learning |
| `ailab-live-state` | Snapshot del sistema |
| `ailab-heartbeat` | Heartbeat persistente del cluster |
| `ailab-metrics` | Dashboard Next.js SSR |
| `ialab-docs` / `ailab-docs` | Portal Astro de documentacion |
| `ailab-runner` | GitHub Actions runner self-hosted |

## Astro

Astro es la capa documental principal.

### Evidencias

- `apps/ialab-docs/package.json` usa `astro build`, `astro dev` y `astro preview`
- `ialab-docs.service` sirve el portal en `:4322`
- el contenido vive en `src/content/docs`, `src/content/runbooks`, `src/content/blog` e `src/content/incidents`
- hay rutas publicas para `docs`, `runbooks`, `blog`, `ops`, `status`, `architecture`, `knowledge`, `infra`, `observability`, `projects`, `services`, `skills`

### Estructura relevante

- `src/pages/docs/[...slug].astro`
- `src/pages/runbooks/[...slug].astro`
- `src/pages/blog/[...slug].astro`
- `src/pages/api/*.ts`
- `src/content/docs/*.md`

## Runtime

El runtime es el nucleo operativo cognitivo.

### Submodulos principales

| Area | Archivos / carpetas |
|---|---|
| Gateway | `runtime/gateway/openai_gateway.py` |
| Router | `runtime/llm/router_api.py`, `runtime/router/capability_router.py` |
| Estado | `runtime/state/*` |
| Distribuido | `runtime/distributed/*` |
| Memoria | `runtime/memory/*` |
| Autonomo | `runtime/autonomous/*` |
| Learning | `runtime/learning/*` |
| Analytics | `runtime/analytics/*` |
| Agent/contexto | `runtime/agent/*` |
| Modo y policy | `runtime/modes/*`, `runtime/policies/*`, `runtime/execution/*` |

### Capacidades implementadas

- gateway OpenAI-compatible con sanitizacion, rate limit y sesiones
- routing por capacidades y scoring adaptativo
- perfiles cognitivos declarativos (`runtime/profiles/`): chat, coding, analysis, observe, agent
- politicas de herramientas (`runtime/policies/tools/`): 3 modos (disabled/readonly/agentic)
- bash sanitizer con `shlex.split()` token scanning
- confirmation gate 428 para write tools
- politicas de memoria (`runtime/policies/memory/`): minimal, light, full
- memory injector con feature flag `AI_LAB_ENABLE_MEMORY_INJECTOR`
- observabilidad 3 canales: stdout, audit, Prometheus
- live state y snapshots persistentes
- heartbeat del cluster y discovery de nodos LM Studio
- analytics de salud, sesiones, routing y eventos
- optimizador autonomo con recomendaciones y cola de acciones

### FASE 20-22 (CP-22B-STABLE)

- modelos estabilizados: llama-3.1-8b (observe), qwen2.5-14b (chat/coding), qwen2.5-32b (reasoning), qwen3.6-27b (agent)
- HARD_FACTS solo en reasoning/analysis
- Plan Mode eliminado
- wrappers legacy limpiados
- 26 hardcodes eliminados, protecciones de seguridad mantenidas
- `sudo reboot`: bloqueado por policy

### Punto de control

- `AI-LAB v1 RC - Native Tool Calls + Tool Fastpath Stable`
- hito alcanzado

### Fase 16

- modo `observe` para analisis tecnico/operativo
- respuestas breves sin `HARD_FACTS` obligatorio
- shell readonly segura: `pwd` y `ls` permitidos, `reboot` bloqueado
- informes técnicos usan un resumen observable mínimo del runtime
- si la request trae `tools`, el routing tool-aware tiene prioridad sobre `observe`

### Fase 17

- `prometheus_client` integrado en runtime con 4 contadores
- endpoint `/metrics` en router (`:8083/metrics`) y gateway (`:8008/metrics`)
- Prometheus `.40` scrapea ambos (jobs: `ai-lab-router`, `ai-lab-gateway`)
- dashboard Grafana `AI-LAB · Panel de Gobernanza`: alertas de seguridad, ratio HARD_FACTS, historico de intercepciones por `reason`
- contador sin labels siempre visible evita "No data" en stats; contador con labels alimenta el desglose
- `ROUTER_REQUESTS.inc()` en cada peticion al router para ratio real (no division por cero)

### Fase 18.1

- modulo `runtime/control/` con `control_plane.py`: agrega estado operacional sin duplicar logica
- 6 endpoints `GET /api/control/*` en live_api (`:8084`): `runtime`, `status`, `nodes`, `routes`, `policies`, `explain/last-route`
- `governance_state`: `NORMAL | ELEVATED | DEGRADED | LOCKDOWN` segun bloqueos, fallbacks, Qdrant
- `/api/control/runtime` ultra-compacto para status bars, CLI checks, mobile

### Estado vivo actual (CP-22B+)

- routing gobernado por perfiles cognitivos (`manifest_profiles.json`)
- herramientas gobernadas por politicas (`manifest_tools.json`, 3 modos)
- memoria gobernada por politicas (`manifest_memory.json`, feature flag)
- nodo GPU activo: `192.168.1.50` (RX9070, 16 GB VRAM)
- LM Studio: `http://192.168.1.50:1234/v1`
- nodo GPU secundario: `192.168.1.60` (RX7900XT, 20 GB VRAM)

## Stacks Docker

### AI core

- `ollama`
- `open-webui`

### Observability

- `grafana`
- `node-exporter`
- `cadvisor`

### Infra y servicios

- `traefik`
- `qdrant`
- `portainer`
- `promtail`

### Websites

- `agithome`
- `agitservices`
- `albertskills`
- `albertskills-amd-multi`
- `calavera-lab`
- `musquera-raw`
- `docs`

## Modelos y nodos GPU

### Configuracion

Archivo: `config/inference_nodes.json`

### Nodos

| Nodo | Host | Rol | VRAM |
|---|---|---|---:|
| `rx9070` | `192.168.1.50` | fast, coding | `16 GB` |
| `rx7900xt` | `192.168.1.60` | reasoning, coding-heavy | `20 GB` |

### Modelos detectados

- `llama-3.1-8b-instruct`
- `qwen2.5-coder-14b-instruct`
- `qwen2.5-coder-32b-instruct`
- `qwen3-14b-claude-sonnet-4.5-reasoning-distill`
- `moondream2-20250414`
- `text-embedding-nomic-embed-text-v1.5`
- `text-embedding-nomic-embed-text-v2-moe`

## Git y estado del repo

- rama: `main`
- remoto: `origin/main`
- HEAD: `22f38614 feat: add live ops center to metrics portal`
- hay artefactos generados en `apps/ialab-docs/dist`, `runtime/state` y `__pycache__`

## Observaciones

- `/opt/ai-lab` es el repo real de trabajo.
- `/mnt/opencode/ai-lab` es el workspace SMB y esta casi vacio.
- Astro es la capa documental principal y no debe confundirse con el dashboard Next.js.
- El runtime esta muy bien instrumentado, pero depende de varios ficheros de estado y servicios en vivo.

## Validacion final Fase 13

### Estado de discovery

- nodos online: `2`
- `rx9070`: online, `3` modelos
- `rx7900xt`: online, `6` modelos
- modelos descubiertos: `9`
- discovery source: `lmstudio`
- fallback activo cuando un nodo cae: confirmado

### Bateria resumida

| Test | Estado | Evidencia |
|---|---|---|
| 1 FAST | ⚠️ | Con el selector corregido cae a `fast`; en ejecuciones anteriores generaba `reasoning` por sesgo de prompt. |
| 2 CODING | ✅ | `qwen2.5-coder-14b-instruct` / `qwen2.5-coder-32b-instruct` segun discovery y ranking. |
| 3 REASONING | ✅ | `qwen2.5-coder-32b-instruct` en `rx7900xt`. |
| 4 Discovery real | ✅ | `selected_model`, `discovery_source`, `reason_codes` y `chat_eligible` expuestos. |
| 5 Embeddings | ✅ | no usa embedding para chat normal. |
| 6 Vision | ✅ | no usa `moondream2` para chat normal. |
| 7 Fallback | ✅ | con `rx9070` offline, cae a `rx7900xt`. |
| 8 Hot-swap | ✅ | tras cargar `qwen2.5-coder-14b-instruct`, el discovery lo ve y puede seleccionarlo. |
| 9 Context stress | ✅ | sin `502` en pruebas previas de carga alta. |
| 10 Auditoria hostil | ✅ | no se detectaron `reason_codes` inventados en la ruta activa. |
| 11 Learning loop | ✅ | patrones y recomendacion de penalizacion por latencia alta. |
| 12 Recall quality | ✅ | incidentes de `high_latency` y `cluster_degraded` recuperados correctamente. |
| 13 Tool use bridge | ✅ | `tool_choice=required` devuelve `tool_calls` estructurado en router y gateway. |

### Ajuste aplicado

- `runtime/llm/model_router.py` ahora trata resúmenes cortos como `fast`, y reconoce `execute_v1_policy`, `whitelist`, `razonamiento` y `reasoning` con mayor estabilidad.
- `runtime/gateway/openai_gateway.py` usa el mismo clasificador de intencion para evitar divergencias entre gateway y router.
- `runtime/agent/intent_router.py` quedo alineado con las mismas palabras clave.
- `tool_use` quedo priorizado para requests que llegan con `tools` o `tool_choice`, y el gateway ya puede seleccionar modelos tool-aware descubiertos en vivo.
- las respuestas de LM Studio con `<tool_call>` se convierten a `tool_calls` OpenAI-native en router y gateway.

## Procedimiento de publicacion Astro

Cuando se modifique `apps/ialab-docs/`:

1. ejecutar `npm run build` en `/opt/ai-lab/apps/ialab-docs`
2. si afecta al portal privado, reiniciar `ailab-docs`
3. verificar con `curl -I http://127.0.0.1:4322/`
4. si debe llegar al sitio publico, hacer `commit` y `push` y dejar que Cloudflare Pages despliegue desde GitHub
