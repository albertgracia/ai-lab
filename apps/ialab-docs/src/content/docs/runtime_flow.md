---
title: "Runtime Flow — Flujo del AI-LAB (CP-22B+)"
summary: "Diagrama actualizado del flujo completo del AI-LAB desde OpenCode/OpenWebUI hasta LM Studio, pasando por perfiles cognitivos, politicas de herramientas y memoria."
order: 12
---

## Entrada

```
OpenWebUI (:3000) / OpenCode / curl
    │
    │ POST /v1/chat/completions
    ▼
Router API (:8083) o Gateway (:8008)
```

## Rutas y modelos

| Ruta virtual | Perfil | Modelo | Nodo |
|-------------|--------|--------|------|
| `ailab-router/auto` (minimal/casual/greet) | observe | llama-3.1-8b-instruct | RX9070 |
| `ailab-router/auto` (fast/general) | chat | qwen2.5-coder-14b-instruct | RX9070 |
| `ailab-router/auto` (coding) | coding | qwen2.5-coder-14b-instruct | RX9070 |
| `ailab-router/auto` (reasoning) | analysis | qwen2.5-coder-32b-instruct | RX9070 |
| `ailab-router/auto` (tool_use) | agent | qwen3.6-27b | RX9070 |

## Flujo completo

```
1. Clasificacion de intencion (is_greeting, is_casual, is_report, is_tool_request)
   └─ tool_request_classifier.py (word-boundary token matching)

2. Asignacion de perfil via manifest_profiles.json
   ├─ minimal/casual/greet/observe → observe_profile (llama-3.1-8b, 96-256 tokens)
   ├─ fast/general → chat_profile (qwen2.5-14b, 512 tokens)
   ├─ coding → coding_profile (qwen2.5-14b, 1024 tokens)
   ├─ reasoning → analysis_profile (qwen2.5-32b, 2048 tokens)
   └─ tool_use/tool_fastpath → agent_profile (qwen3.6-27b, 2048 tokens)

3. Politica de herramientas via manifest_tools.json
   ├─ disabled → pop tools (minimal/observe/chat/analysis)
   ├─ readonly → filtrar allowed_names (coding)
   └─ agentic → preservar con confirmation gate (tool_use)

4. Politica de memoria via manifest_memory.json (FASE 23A)
   ├─ minimal → sin recall (observe)
   ├─ light → 1 memoria, 800 chars, solo incidents (chat, coding)
   └─ full → 5 memorias, episodic, runtime state (analysis, agent)

5. Bash sanitizer (FASE 22B)
   └─ shlex.split() token scanning. Pipes/redirects bloqueados por modo.

6. Gateway confirmation gate (FASE 22B)
   └─ 428 Precondition Required para write tools en modo agentic

7. POST a LM Studio (192.168.1.50:1234/v1)

8. Sanitizacion de respuesta (tool_call filtering, reasoning stripping)

9. Respuesta SSE/JSON a OpenWebUI/OpenCode
```

## Modelos por GPU

| Nodo | IP | Modelos cargados | VRAM |
|------|----|-----------------|------|
| RX9070 | 192.168.1.50:1234 | llama-3.1-8b, qwen2.5-14b, qwen2.5-32b, qwen3.6-27b, nomic-embed | 16 GB |
