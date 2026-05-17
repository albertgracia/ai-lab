---
title: "Runbook Informe Completo AI-LAB"
summary: "Procedimiento de solo lectura para auditar la VM, Astro, runtime, servicios y stacks del laboratorio."
status: "stable"
category: "operations"
date: "2026-05-16"
tags:
  - ai-lab
  - audit
  - runtime
  - astro
  - infrastructure
---

# Runbook de auditoria completa

## Objetivo

Obtener una fotografia completa de AI-LAB sin modificar nada.

## Alcance

- VM Hyper-V y Ubuntu
- almacenamiento y montajes
- servicios systemd
- Astro docs
- runtime cognitivo
- stacks Docker
- nodos GPU y LM Studio

## 1. Base del sistema

```bash
hostnamectl
uname -a
df -hT
mount
free -h
```

## 2. Red y servicios

```bash
ip -br addr
ss -tulpn
systemctl list-units --type=service --state=running --no-pager
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```

## 3. Estructura del repositorio

```bash
for d in /opt/ai-lab/*; do [ -d "$d" ] && basename "$d"; done
for d in /opt/ai-lab/apps/*; do [ -d "$d" ] && basename "$d"; done
for d in /opt/ai-lab/stacks/*; do [ -d "$d" ] && basename "$d"; done
```

## 4. Astro

Revisar:

- `apps/ialab-docs/package.json`
- `apps/ialab-docs/src/content/docs/*`
- `apps/ialab-docs/src/content/runbooks/*`
- `apps/ialab-docs/src/pages/*`

Compilacion:

```bash
cd /opt/ai-lab/apps/ialab-docs
npm run build
```

Verificacion local:

```bash
curl -I http://127.0.0.1:4322/
```

## 5. Runtime

Revisar:

- `runtime/gateway/openai_gateway.py`
- `runtime/llm/router_api.py`
- `runtime/state/live_api.py`
- `runtime/distributed/heartbeat.py`
- `runtime/memory/recall_policy.py`
- `runtime/autonomous/runtime_optimizer.py`
- `runtime/execution/execute_v1_policy.py`

Estado vivo:

```bash
cat /opt/ai-lab/runtime/state/current_mode.json
cat /opt/ai-lab/runtime/state/cluster_state.json
```

## 6. Stacks críticos

- `stacks/traefik/docker-compose.yml`
- `stacks/ai-core/docker-compose.yml`
- `stacks/observability/docker-compose.yml`
- `stacks/qdrant/docker-compose.yml`
- `stacks/websites/docker-compose.yml`
- `stacks/websites/docker-compose.backend.yml`

## 7. Publicacion Astro

Si se cambia `apps/ialab-docs/`:

1. ejecutar `npm run build`
2. reiniciar `ailab-docs.service`
3. verificar `curl -I http://127.0.0.1:4322/`
4. si aplica al sitio publico, hacer `commit` y `push`; el despliegue publico se completa via GitHub -> Cloudflare Pages

## 8. Criterios de salida

La auditoria esta completa cuando quedan identificados:

- sistema base
- puertos y servicios
- Astro y rutas publicadas
- runtime y estado vivo
- stacks Docker
- nodos GPU y LM Studio

## 9. Validacion final Fase 13

Usar esta bateria cuando el cluster ya esta estable:

| Test | Comportamiento esperado | Estado final |
|---|---|---|
| 1 FAST | `llama-3.1-8b-instruct` y respuesta breve | ⚠️ selector corregido; respuesta puede quedar en `reasoning` si el prompt arrastra sesgo |
| 2 CODING | `qwen2.5-coder-14b-instruct` o `qwen2.5-coder-32b-instruct` | ✅ |
| 3 REASONING | `qwen2.5-coder-32b-instruct` en `rx7900xt` | ✅ |
| 4 Discovery | `selected_model`, `reason_codes`, `discovery_source` | ✅ |
| 5 Embeddings | nunca `text-embedding-*` para chat | ✅ |
| 6 Vision | nunca `moondream2` para chat | ✅ |
| 7 Fallback | con `rx9070` offline, caer a `rx7900xt` | ✅ |
| 8 Hot-swap | detectar el modelo nuevo en refresh | ✅ |
| 10 Hostile audit | no inventar `reason_codes` ni `HARD_FACTS` | ✅ |
| 11 Learning | crear/actualizar patrones y recomendaciones | ✅ |
| 12 Recall | recuperar incidentes reales de latencia/overflow | ✅ |

## 10. Notas de operacion

- Si `:8083` o `:8008` quedan colgados, reiniciar el proceso via systemd o forzar el PID que ocupa el puerto.
- Si `rx9070` cae, el discovery debe marcarlo offline sin romper routing.
- Si se cambia el clasificador de intencion, alinear router, gateway y cualquier wrapper local en la misma heuristica.
