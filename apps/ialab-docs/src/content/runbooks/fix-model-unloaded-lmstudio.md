---
title: "Runbook — Model Unloaded en LM Studio"
summary: "Procedimiento de diagnostico y recuperacion ante el error 'Model unloaded.' que afecta al router AI-LAB cuando LM Studio descarga el modelo por TTL."
---

# Runbook — Model Unloaded en LM Studio

## Síntoma

OpenCode, OpenWebUI o cualquier cliente OpenAI-compatible devuelve:

```
"Model unloaded."
```

O en formato SSE:

```
event: error
data: {"error": {"message": "Model unloaded."}}
```

## Diagnóstico rápido

```bash
# 1. ¿Responde el router?
curl -s http://192.168.1.30:8083/health

# 2. ¿Responde LM Studio directo? (2 llamadas seguidas)
curl -s --max-time 20 http://192.168.1.50:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instruct","messages":[{"role":"user","content":"hola"}],"max_tokens":10}'
sleep 2
curl -s --max-time 20 http://192.168.1.50:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.1-8b-instruct","messages":[{"role":"user","content":"hola"}],"max_tokens":10}'
```

Si la primera responde 200 y la segunda 400, LM Studio tiene el TTL activo.

# 3. ¿El router maneja el reintento?
curl -s --max-time 60 http://192.168.1.30:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ailab-router/auto","messages":[{"role":"user","content":"hola"}],"max_tokens":20}'
```

Si responde correctamente, el reintento del router está funcionando.

## Causas

| Causa | Síntoma | Solución |
|---|---|---|
| LM Studio TTL expiration | El modelo se descarga tras cada respuesta | Ver logs LM Studio: `Unloading model ... due to TTL expiration` |
| Modelo no cargado en VRAM | Primera llamada 400, segunda 200 | El router ya reintenta automáticamente |
| Modelo inválido en nodo | "Invalid model identifier" | El router hace fallback a `.50:1234` con `llama-3.1-8b-instruct` |
| OpenCode pide streaming pero router devuelve JSON | Chat vacío | Verificar que el router tiene el SSE wrapper activo |
| OpenWebUI apunta a LM Studio directo | Error 400 constante | Cambiar `OPENAI_API_BASE_URL` al router |

## Recuperación

### Recuperación automática (ya implementada)

El router y el gateway reintentan automáticamente cuando detectan:
- `"Model unloaded."` → reintenta misma petición (fuerza recarga del modelo)
- `"Invalid model identifier"` → redirige a `192.168.1.50:1234` con `llama-3.1-8b-instruct`

### Recuperación manual

```bash
# 1. Verificar servicios
systemctl status ailab-router ailab-gateway

# 2. Reiniciar si es necesario
sudo systemctl restart ailab-router ailab-gateway

# 3. Forzar rediscovery de modelos
curl -s http://192.168.1.30:8084/api/models/discovery/refresh

# 4. Verificar LM Studio .50
curl -s http://192.168.1.50:1234/v1/models | python3 -m json.tool

# 5. Verificar LM Studio .60
curl -s http://192.168.1.60:1234/v1/models | python3 -m json.tool
```

### OpenCode no renderiza respuestas

1. Verificar `~/.config/opencode/opencode.jsonc`:
   ```json
   {
     "provider": {
       "ailab-router": {
         "options": {
           "baseURL": "http://192.168.1.30:8083/v1",
           "apiKey": "ailab"
         },
         "models": {
           "ailab-router/auto": { "name": "ailab-router/auto" },
           "ailab-router/fast": { "name": "ailab-router/fast" }
         }
       }
     }
   }
   ```
2. Reiniciar OpenCode: `pkill -f ".opencode" && nohup opencode web --hostname 0.0.0.0 --port 8082 &`

### OpenWebUI no responde

```bash
cd /opt/ai-lab/stacks/ai-core
docker rm -f open-webui
docker compose up -d open-webui
```

Verificar que `OPENAI_API_BASE_URL=http://host.docker.internal:8083/v1`.

## LM Studio TTL

El TTL de LM Studio **no es configurable desde la UI** con idle timeout. Si el modelo se descarga tras cada respuesta, el router ya maneja la recarga automática. Para desactivar completamente el TTL, editar el archivo de configuración de LM Studio (varía según la versión).
