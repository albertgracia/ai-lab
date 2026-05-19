---
title: "FASE 94 — HARD FACTS (arquitectura actual CP-22B+)"
summary: "Sistema de grounding con datos reales del runtime. Ahora activo solo en rutas reasoning/analysis. Las rutas ligeras usan prompts declarativos sin HARD_FACTS."
order: 20
---

## Concepto

HARD FACTS inyecta datos reales del runtime AI-LAB en el system prompt para reasoning/analysis. Las rutas ligeras (minimal, casual, greeting, observe, fast, general, coding) NO reciben HARD FACTS.

## Jerarquia actual

```
route → manifest_profiles.json → profile → manifest_memory.json → memory policy
```

- `minimal/casual/greeting/observe` → `observe_profile.json` → `minimal_policy.json` (sin memory, sin HARD_FACTS)
- `fast/general/chat` → `chat_profile.json` → `light_policy.json` (memory ligera, sin HARD_FACTS)
- `coding` → `coding_profile.json` → `light_policy.json` (memory ligera, sin HARD_FACTS)
- `reasoning` → `analysis_profile.json` → `full_policy.json` (memory completa + HARD_FACTS)
- `tool_use/tool_fastpath` → `agent_profile.json` → `full_policy.json` (memory completa + HARD_FACTS)

## Donde se usa ahora

HARD_FACTS solo se activa cuando `full_policy.json` de memoria esta activa y tiene `inject_runtime_state: true`. Esto ocurre para `analysis` y `agent` profiles.

El formato se construye en `context_shaper.py` via `_build_hard_facts()` y se inyecta en el system prompt del router. Las rutas ligeras usan prompts declarativos de `runtime/prompts/*.md` con `forbidden_markers` que prohiben HARD_FACTS.

## Prompts declarativos (FASE 20C)

Los prompts estan en `runtime/prompts/`:

```text
runtime/prompts/
├── manifest.json           # Mapeo route → prompt + forbidden markers
├── chat_prompt.md
├── coding_prompt.md
├── reasoning_prompt.md
├── observe_prompt.md
├── minimal_prompt.md
└── tool_use_prompt.md
```

El `manifest.json` define `forbidden_markers` que rechazan prompts con HARD_FACTS en rutas ligeras:

```json
{
  "forbidden_markers": {
    "minimal": ["HARD_FACTS", "Plan Mode", "FORMATO OBLIGATORIO"],
    "chat": ["HARD_FACTS", "Plan Mode", "FORMATO OBLIGATORIO"],
    "coding": ["HARD_FACTS", "Plan Mode"],
    "observe": ["HARD_FACTS", "Plan Mode", "FORMATO OBLIGATORIO"]
  }
}
```

## Observabilidad

- `HARD_FACTS_HITS`: contador Prometheus de cuantas veces se construyo contexto HARD_FACTS
- Profile metrics: `ailab_profile_total{profile, route_family, model}`
- Memory metrics: `ailab_memory_recall_total{policy, hit}`
