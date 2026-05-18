---
title: "Runbook — FASE 20 Router Qwen 2.5"
summary: "Runbook unificado para operar y verificar las FASEs 20A y 20B del AI-LAB Router tras la migracion a qwen2.5-coder-14b-instruct."
order: 42
---

## Objetivo

Verificar que el AI-LAB Router usa los modelos correctos segun la ruta y que los wrappers legacy estan limpios en rutas no cognitivas.

## Modelos por ruta

| Ruta | Modelo esperado | max_tokens |
|------|----------------|-----------|
| minimal/casual | llama-3.1-8b-instruct | ~96 |
| minimal/greeting | llama-3.1-8b-instruct | ~96 |
| minimal/report | llama-3.1-8b-instruct | ~180 |
| observe | llama-3.1-8b-instruct | ~180 |
| fast | qwen/qwen2.5-coder-14b-instruct | 256 |
| general | qwen/qwen2.5-coder-14b-instruct | 768 |
| coding | qwen/qwen2.5-coder-14b-instruct | 768 |
| reasoning | qwen2.5-coder-32b-instruct | 1200 |
| tool_use | qwen/qwen3.6-27b | 768 |

## Checks rapidos

### Router (8083)

```bash
# minimal
curl -sS -D- http://127.0.0.1:8083/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"hola"}],"stream":false,"max_tokens":16,"temperature":0}' | grep x-ai-lab-selected-model

# fast
curl -sS -D- http://127.0.0.1:8083/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"fast","messages":[{"role":"user","content":"que es docker"}],"stream":false,"max_tokens":16,"temperature":0}' | grep x-ai-lab-selected-model
```

### Gateway (8008)

```bash
# casual con tools
curl -sS http://127.0.0.1:8008/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","tool_choice":"auto","tools":[{"type":"function","function":{"name":"question","description":"ask"}}],"messages":[{"role":"user","content":"podrias decirme que puedes hacer?"}],"stream":false,"max_tokens":32,"temperature":0}' | python3 -m json.tool | grep -E '"model"|prompt_tokens'

# general
curl -sS http://127.0.0.1:8008/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"auto","messages":[{"role":"user","content":"que es docker"}],"stream":false,"max_tokens":64,"temperature":0}' | python3 -m json.tool | grep -E '"model"|prompt_tokens'
```

## Sintomas y soluciones

| Sintoma | Causa probable | Accion |
|---------|---------------|--------|
| `qwen3.6-27b` en ruta general | `choose_model()` sin override | Verificar FASE 20B en gateway |
| 502 con `no usable choices` | Router directo a LM Studio | Usar gateway (8008) |
| `prompt_tokens > 1000` en minimal | `max_tokens` override bug | Verificar FASE 20B en gateway |
| Respuesta con `[HARD_FACTS]` en fast | `build_system_context()` incorrecto | Verificar FASE 20B en router |

## Rollback

```bash
# FASE 20A
cp /opt/ai-lab/snapshots/fase20a-backup/* /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase20a-backup/inference_nodes.json /opt/ai-lab/config/

# FASE 20B
cp /opt/ai-lab/snapshots/fase20b-backup/router_api.py /opt/ai-lab/runtime/llm/
cp /opt/ai-lab/snapshots/fase20b-backup/openai_gateway.py /opt/ai-lab/runtime/gateway/

sudo systemctl restart ailab-router ailab-gateway
```

## Panel de soporte

- Dashboard: `AI-LAB Route Family Observability Baseline`
- URL: `http://192.168.1.40:3000/d/ai-lab-route-family/ai-lab-route-family-observability-baseline`

## Documentacion relacionada

- `/docs/fase-20a-migracion-qwen2.5-14b`
- `/docs/fase-20b-limpieza-wrappers-legacy`
