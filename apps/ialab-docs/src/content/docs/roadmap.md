---
title: "ROADMAP — AI-LAB Arquitectura Final"
summary: "Hoja de ruta completa del AI-LAB desde FASE 20 hasta FASE 30. Arquitectura objetivo: runtime cognitivo local-first estable, multi-modelo, observable y seguro."
order: 1
---

## Visión

AI-LAB debe convertirse en un **runtime cognitivo local-first estable**: OpenCode / OpenWebUI / APIs → AI-LAB Router → perfiles cognitivos → memoria semántica limpia → tools controladas → scheduler multi-GPU → LM Studio nodes → observabilidad completa.

---

## FASE 20A — Modelo principal Qwen 2.5 Coder 14B

**Estado:** completada

Migración del modelo por defecto del router a `qwen/qwen2.5-coder-14b-instruct` para las rutas `fast`, `general` y `coding`. Las rutas ligeras (`minimal`, `casual`, `greeting`, `observe`) mantienen `llama-3.1-8b-instruct`.

Ver: `/docs/fase-20a-migracion-qwen2.5-14b`

---

## FASE 20B — Limpieza wrappers legacy

**Estado:** completada

Eliminación de HARD_FACTS automáticos, Plan Mode, reasoning wrappers, structured JSON y tool forcing de las rutas `fast`, `general` y `coding`. Las rutas `reasoning` y `tool_use` mantienen su comportamiento.

Ver: `/docs/fase-20b-limpieza-wrappers-legacy`

---

## FASE 20C — Normalización de prompts runtime

**Estado:** completada

**Objetivo:** Separar definitivamente los prompts por tipo de ruta sin cambiar arquitectura.

- prompts de chat
- prompts coding
- prompts reasoning
- prompts observe
- prompts tool_use

Actualmente existe "legacy semantic leakage" que mezcla contexto entre rutas.

**20C debe:**
- Centralizar prompts
- Versionarlos
- Hacerlos declarativos
- Evitar inyección accidental
- Evitar HARD_FACTS globales
- Evitar wrappers heredados

**Arquitectura objetivo:**

```
runtime/prompts/
├── chat_prompt.md
├── coding_prompt.md
├── reasoning_prompt.md
├── observe_prompt.md
├── tool_use_prompt.md
└── minimal_prompt.md
```

---

## FASE 21 — Perfiles cognitivos

**Estado:** 21A + 21A.1 + 21B completadas (CP-21B-STABLE)

- 21A: Policy bundles declarativos en `runtime/profiles/`
- 21A.1: Observabilidad de perfiles (stdout + audit + Prometheus)
- 21B: De-hardcoding progresivo (26 hardcodes eliminados, 7 protegidos)

**Objetivo:** Crear perfiles de comportamiento sin romper el routing existente.

- CHAT_PROFILE
- CODING_PROFILE
- ANALYSIS_PROFILE
- AGENT_PROFILE
- OBSERVE_PROFILE

**La diferencia clave:**
- **FASE 20C** → limpiar prompts (sin cambiar comportamiento)
- **FASE 21** → cambiar comportamiento cognitivo (usando prompts limpios)

No mezclarlas es lo que mantiene AI-LAB estable.

---

## FASE 22 — Tool Runtime controlado

**Estado:** 22A + 22B completadas (CP-22B-STABLE)

- 22A: Politicas declarativas (`runtime/policies/tools/`): disabled/readonly/agentic
- 22B: Bash sanitizer (`shlex.split()`), confirmation gate 428, auditoria por tool_call
- 22B.1: Fix clasificador greetings (word-boundary token matching)

---

## FASE 23 — Memoria semántica estable

**Estado:** 23A completada (CP-23A-MEMORY-SAFE)

- `runtime/policies/memory/`: 3 politicas (minimal/light/full)
- Memory injector con items API + feature flag `AI_LAB_ENABLE_MEMORY_INJECTOR`
- Skip rules (query < N palabras → sin Qdrant)
- Episodic solo en full policy

---

## FASE 24 — Observabilidad cognitiva

**Estado:** avanzada (3 canales activos)

- stdout: `profile=chat route=cognitive model=qwen2.5-14b`
- Audit: `governance_audit.jsonl` con `profile_applied`, `tool_call_allowed`
- Prometheus: `ailab_profile_total`, `ailab_tool_call_total`, `ailab_memory_recall_total`

---

## FASE 25 — Scheduler multi-GPU

**Objetivo:** Decidir dinámicamente entre RX9070, RX7900XT y otros nodos LM Studio según carga y modelo.

---

## FASE 26 — OpenCode production profile

**Objetivo:** Perfil estable para desarrollo real sin Plan Mode accidental ni wrappers.

---

## FASE 27 — OpenWebUI production profile

**Objetivo:** Chat limpio, memoria controlada y sin follow_ups inesperados.

---

## FASE 28 — Runtime autónomo seguro

**Objetivo:** Workflows agentic con permisos, dry-run, aprobación humana y rollback.

---

## FASE 29 — AI-LAB Dashboard v2

**Objetivo:** Panel único de estado vivo: modelos, nodos, memoria, GPU, Docker, router, agentes.

---

## FASE 30 — AI-LAB v1.0 estable

**Objetivo final:** Laboratorio IA local-first, multi-modelo, observable, reversible y usable en producción doméstica/técnica.

---

## Arquitectura objetivo final

```
OpenCode / OpenWebUI / APIs
        ↓
AI-LAB Router
        ↓
perfiles cognitivos
        ↓
memoria semántica limpia
        ↓
tools controladas
        ↓
scheduler multi-GPU
        ↓
LM Studio nodes
        ↓
observabilidad completa
```

---

## Principios de diseño

| Principio | Descripción |
|-----------|-------------|
| **Rápido para trivial** | `minimal/casual` → llama-3.1-8b, sin contexto |
| **Potente para útil** | `fast/general/coding` → qwen2.5-14b, contexto ligero |
| **Pesado solo cuando hace falta** | `reasoning` → qwen2.5-32b, `tool_use` → qwen3.6-27b |
| **No mezclar fases** | Separar limpieza de prompts (20C) de cambio cognitivo (21) |
| **Rollback siempre** | Cada fase tiene snapshot de backup |
