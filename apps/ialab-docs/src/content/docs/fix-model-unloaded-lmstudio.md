---
title: "Fix — Resiliencia ante Model Unloaded de LM Studio"
summary: "Diagnostico y solucion del error 'Model unloaded.' que afectaba a OpenCode y OpenWebUI tras FASE 18. El modelo se descargaba por TTL de LM Studio y el router/gateway necesitaban compatibilidad SSE estable con retry y fallback."
order: 37
---

## Problema

Tras desplegar FASE 18, OpenCode y OpenWebUI devolvían `"Model unloaded."` en cada petición. El router AI-LAB funcionaba correctamente desde curl, pero los clientes que usaban streaming fallaban.

## Diagnóstico

Se identificaron 3 causas encadenadas:

### 1. LM Studio — TTL expiration

El log de LM Studio mostraba:

```
Unloading model llama-3.1-8b-instruct due to TTL expiration.
```

El modelo se descargaba de VRAM tras **cada respuesta**. Aunque el idle timeout estaba configurado a `99999999`, LM Studio tiene un TTL independiente que fuerza la descarga. Esto provocaba que la segunda petición consecutiva recibiera `"Model is unloaded."`

### 2. Errores dentro del SSE

Cuando LM Studio devolvía `"Model is unloaded."` en una petición con `stream: true`, el error se incrustaba dentro del stream SSE con HTTP 200:

```
event: error
data: {"error": {"message": "Model unloaded."}}
```

El router no inspeccionaba el contenido del stream y reenviaba el error tal cual. Los clientes (OpenCode, OpenWebUI) no renderizaban la respuesta.

### 3. OpenCode sin SSE wrapper

El router eliminaba `"stream": true` del payload para evitar los errores en SSE, pero devolvía la respuesta como JSON plano. OpenCode, al haber pedido streaming, esperaba chunks SSE y no renderizaba el JSON.

## Solución

### Router API (`runtime/llm/router_api.py`)

- **Retry + fallback**: si LM Studio responde 400 con `"unloaded"` o `"invalid model identifier"`, reintenta automáticamente. Si el reintento falla, redirige a `192.168.1.50:1234` con `llama-3.1-8b-instruct`
- **SSE compatible para cliente**: el router devuelve chunks OpenAI/SSE válidos al cliente, pero no rompe el payload interno del backend
- **No reenvía `stream=true` al backend**: LM Studio recibe completaciones estables y el streaming se resuelve aguas arriba

### Gateway (`runtime/gateway/openai_gateway.py`)

- Mismo patrón: limpia `stream` antes de hablar con LM Studio
- Retry en `"Model unloaded."`
- Devuelve SSE compatible al cliente cuando se pidió streaming

### OpenWebUI (`stacks/ai-core/docker-compose.yml`)

- `OPENAI_API_BASE_URL` cambiado de `http://192.168.1.50:1234` (LM Studio directo) a `http://host.docker.internal:8083/v1` (AI-LAB Router)

### OpenCode (`~/.config/opencode/opencode.jsonc`)

- Modelos corregidos: `ailab-router/auto`, `ailab-router/fast`, `ailab-router/coding`, `ailab-router/reasoning`
- Añadido `apiKey: ailab`

## Verificación

```bash
# SSE streaming (5/5 OK)
for i in 1 2 3 4 5; do
  curl -s --max-time 60 -X POST http://192.168.1.30:8083/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"ailab-router/auto","stream":true,"messages":[{"role":"user","content":"hola"}],"max_tokens":20}' | grep "DONE"
done

# No-streaming (3/3 OK)
for i in 1 2 3; do
  curl -s --max-time 60 -X POST http://192.168.1.30:8083/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"ailab-router/auto","messages":[{"role":"user","content":"hola"}],"max_tokens":20}' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
done
```

## Resultado

- OpenCode: responde correctamente con streaming
- OpenWebUI: responde correctamente via router AI-LAB
- Curl: ambas rutas (SSE y JSON) estables
- 0 errores, 0 "Model unloaded." residual

## Actualización posterior

Más tarde se detectó un segundo problema operativo en la capa de interacción: algunas respuestas de resumen intentaban usar la herramienta `question` con `questions` serializado como string. Eso se documentó aparte en `parche-opencode-router-gateway.md` para evitar confundir un bug de herramienta con un bug de runtime.

## Archivos modificados

| Archivo | Cambio |
|---|---|
| `runtime/llm/router_api.py` | SSE wrapper + retry + fallback |
| `runtime/gateway/openai_gateway.py` | No-streaming + retry |
| `stacks/ai-core/docker-compose.yml` | OpenWebUI → router |
| `~/.config/opencode/opencode.jsonc` | Modelos corregidos |
