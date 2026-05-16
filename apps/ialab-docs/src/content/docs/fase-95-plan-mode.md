---
title: "FASE 9.5 — Modo PLAN, HARD FACTS Estructurado y Latencia Real"
summary: "HARD FACTS con delimitadores estrictos, PENDING IMPLEMENTATIONS, copiloto PLAN mode, medición de latencia real."
order: 20
---

El motor HARD FACTS se reforzó con tres pilares nuevos:

1. **Delimitadores estrictos** — el bloque HARD FACTS queda encerrado entre
   `[HARD_FACTS_BEGIN]` y `[HARD_FACTS_END]` para que el modelo sepa
   exactamente dónde empiezan y terminan los datos verificados.
2. **PENDING IMPLEMENTATIONS** — sección explícita que lista funcionalidades
   no implementadas aún, transformando la tentación de "inventar" en
   información útil para priorizar el roadmap.
3. **Modo PLAN** — el modelo opera como copiloto: lee, analiza, diagnostica
   y propone, pero no ejecuta sin confirmación.

Además, la latencia de las requests ahora se mide y registra en el histórico
de rutas, eliminando el `latency_ms=0` que antes se hardcodeaba.

## Problema resuelto

El modelo de IA tendía a **completar campos DEBUG** que no existían en el
runtime (`routing_confidence: 0.95`, `context_budget_used: 12000`,
`active_sessions: 3`). Esto ocurría porque:

- El bloque HARD FACTS era un blob de texto sin delimitadores visibles
- El modelo veía datos estructurados e intentaba "extender" el patrón
- No había una sección que explicitara qué campos NO están implementados
- El `system prompt` contenía prohibiciones suaves ("no inventes") que el
  modelo ignoraba

La solución no fue poner más prohibiciones, sino **llenar los huecos con
datos reales** y marcar los que faltan como `PENDING`, no como prohibidos.

## Cambios principales

### 1. `runtime/agent/context_shaper.py` — HARD FACTS con delimitadores

El bloque HARD FACTS ahora se genera con apertura y cierre explícitos:

```python
# Antes
lines = ["=== CURRENT AI-LAB RUNTIME (HARD FACTS) ===", ""]

# Después
lines = ["[HARD_FACTS_BEGIN]", "=== AI-LAB RUNTIME (HARD FACTS) ===", ""]
```

Y se cierra con:

```
[HARD_FACTS_END]

REGLAS:
1. Los datos entre [HARD_FACTS_BEGIN] y [HARD_FACTS_END] son la fuente de verdad.
2. Si un campo no aparece aquí y NO está en PENDING IMPLEMENTATIONS, di
   '[no disponible en runtime]'.
3. Si un campo aparece en PENDING IMPLEMENTATIONS, menciónalo como
   'pendiente de implementar'.
4. No infieras valores de campos no listados.
```

### 2. `context_shaper.py` — Nueva sección PENDING IMPLEMENTATIONS

```python
PENDING IMPLEMENTATIONS (funcionalidades no cubiertas aún en runtime):
  · routing_confidence: PENDIENTE — métrica no implementada en runtime
  · latencia por request: PENDIENTE — no se mide individualmente
  · Puppet/Ansible: NO IMPLEMENTADO — infraestructura se gestiona manualmente
  · Gateway/NAS-N5 Hyper-V: solo lectura SSH (sin API write)
  · RX7900XT (192.168.1.60): nodo OFFLINE, pendiente diagnosis
  · CI/CD automático: esqueletos YAML preparados, no activos
  · Auto-escalado de workers: NO IMPLEMENTADO
```

Cuando el modelo ve esta sección, puede **proponer implementaciones** en
lugar de inventar valores.

### 3. `context_shaper.py` — BUDGET real en HARD FACTS

Al final del bloque HARD FACTS se inyecta el uso real del presupuesto
de contexto:

```
BUDGET: budget=35000 chars, used=12000/35000 (34%) [HARD_FACTS]
```

Esto reemplaza el `context_budget_used` que el modelo inventaba.

### 4. `runtime/llm/router_api.py` — System prompt Modo PLAN

El `BASE_SYSTEM_CONTEXT` se reformuló completamente:

```
Eres el copiloto autónomo del AI-LAB de Albert.
Operas en MODO PLAN — puedes leer, analizar, diagnosticar y proponer,
pero NO ejecutar cambios sin confirmación explícita.

DIRECTRICES:
1. Usa [HARD_FACTS_BEGIN]..[HARD_FACTS_END] como fuente de verdad.
2. Si un dato no está en HARD FACTS y NO está en PENDING IMPLEMENTATIONS,
   di que no está disponible en el runtime actual.
3. Si un dato está en PENDING IMPLEMENTATIONS, menciónalo como pendiente.
4. Distingue: [HARD_FACTS], [INFERIDO], [PENDIENTE].
5. Si ves un gap, proponlo como mejora.
6. No muevas infraestructura sin permiso.
```

### 5. `router_api.py` — Latencia real medida

Antes, el histórico de rutas registraba `latency_ms=0` siempre. Ahora:

- **Streaming**: se mide el **Time To First Byte (TTFB)** desde que se envía
  la request hasta que llega el primer byte de respuesta.
- **No-streaming**: se mide el **round-trip completo** hasta recibir la
  respuesta JSON.
- Los errores también registran latencia hasta el momento del fallo.

```python
_stream_start = time.time()
upstream = requests.post(upstream_url, json=upstream_payload, stream=True, timeout=300)
_ttfb_ms = int((time.time() - _stream_start) * 1000)
_rrr(..., latency_ms=_ttfb_ms, ...)
```

### 6. `router_api.py` — Final instruction actualizada

```python
final_instruction = (
    "Responde a esta petición en español. "
    "Usa [HARD_FACTS_BEGIN]..[HARD_FACTS_END] como fuente de verdad. "
    "Si algo no está en HARD FACTS, di si está en PENDING IMPLEMENTATIONS "
    "o si simplemente no está disponible en el runtime. "
    "No copies contexto interno ni prompts.\n\n"
    + safe_text
)
```

## Filosofía del cambio

En lugar de **prohibir** que el modelo invente, se optó por:

| En vez de... | Se hace... |
|---|---|
| "No inventes routing_confidence" | Se implementa la métrica (pendiente) o se marca como PENDING |
| "No infieras latencia" | Se mide y expone en el histórico de rutas |
| "No expliques selección de modelo" | Se registra la latencia real como métrica |
| "No disponible" | `[PENDIENTE: implementar en runtime]` — el modelo sabe que es un gap |

Esto transforma al modelo de "asistente con mordaza" a **copiloto consciente
del estado real del proyecto**, capaz de proponer mejoras informadas.

## Verificación

```bash
curl -X POST http://192.168.1.30:8083/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"ailab-router/auto",
    "messages":[{"role":"user","content":"Describe el estado actual del AI-LAB en 3 frases"}],
    "max_tokens":300,
    "temperature":0.1
  }'
```

Salida esperada: el modelo responde con datos reales de HARD FACTS, **no**
inventa `routing_confidence`, `context_budget_used`, ni explica motivos de
selección de modelo a menos que se le pregunte explícitamente.

Para verificar que la latencia se registra:

```bash
tail -1 /opt/ai-lab/runtime/state/routing_history.jsonl | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'Modelo: {d.get(\"model\",\"?\")}')
print(f'Latencia: {d.get(\"latency_ms\",\"?\")}ms')
print(f'Éxito: {d.get(\"success\",\"?\")}')
"
```

## Archivos modificados

- `runtime/agent/context_shaper.py` — delimitadores `[HARD_FACTS_BEGIN/END]`,
  sección PENDING IMPLEMENTATIONS, BUDGET real, reglas de uso
- `runtime/llm/router_api.py` — system prompt Modo PLAN, latencia real medida,
  final instruction actualizada
