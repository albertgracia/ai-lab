---
title: "FASE 29.3.1 — Routing Tightening & Latency Optimization"
summary: "Optimización determinista del routing para que greetings, short prompts y observe vayan siempre a llama-3.1-8b. qwen2.5-14b se reserva para coding, architecture y reasoning profundo. 48 greeting markers, is_lightweight_prompt(), QWEN_ESCALATION_REASONS."
order: 71
---

## Objetivo

Conseguir que greetings, smalltalk, prompts cortos y observe básico vayan SIEMPRE a llama-3.1-8b, reservando qwen2.5-coder-14b solo para coding, architecture, reasoning y debugging.

## Problema detectado

Tras FASE 29.3 (three-model runtime), se detectó que saludos como "adios", "vale", "genial", "perfecto" y prompts triviales como "si", "no", "claro" seguían activando qwen2.5-14b innecesariamente. El `is_greeting_request()` solo reconocía 11 marcadores exactos.

## Solución

### Greeting Fastpath (48 marcadores)

```python
_GREETING_MARKERS = (
    "hola", "buenas", "adios", "gracias", "ok", "vale", "genial",
    "perfecto", "claro", "entendido", "si", "no", "de acuerdo",
    "hello", "hi", "thanks", "bye", "yes", "yeah", "nope", ...
)
```

48 marcadores cubriendo español e inglés. Token-based fallback con `len(tokens) <= 1` para detectar cualquier saludo corto no listado.

### Lightweight Prompt Heuristic

```python
def is_lightweight_prompt(text: str) -> bool:
    if len(text) < 120 and no code_fences and no_architecture_keywords:
        return True  # → llama-3.1-8b
```

### QWEN_ESCALATION_REASONS

9 razones deterministas para activar qwen2.5-14b:

| Razón | Disparador |
|-------|-----------|
| `coding_explicit` | Code fences, function writing |
| `architecture_deep` | Multi-step analysis keywords |
| `debugging` | Stacktrace, traceback, exception |
| `long_context` | Prompt > 500 chars técnico |
| `multi_step` | Multi-file planning |
| `reasoning_deep` | "analiza", "razona", "compara" |
| `report_technical` | "informe", "report", "documentación" |

### Observe Override Fix

El observe fastpath forzaba llama incluso para análisis profundos. Corregido: si `get_qwen_escalation_reason()` detecta motivo de escalada, el observe no fuerza llama.

## Validación

13/13 tests PASS:
- Todos los greetings → llama ✅
- Coding → qwen2.5 ✅
- Architecture → qwen2.5 ✅
- Short trivia → llama ✅

## Métricas nuevas

- `ailab_greeting_fastpath_total`
- `ailab_qwen_escalation_total`
- `ailab_llama_fastpath_total`
