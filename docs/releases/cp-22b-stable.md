# AI-LAB — Release CP-22B-STABLE

**Tag:** `CP-22B-STABLE`
**Fecha:** 2026-05-19
**Estado:** Producción (tool runtime gobernado)

---

## Hito

Primer release con runtime de herramientas gobernado por políticas declarativas. Se completaron las capas de governance (22A), execution safety (22B), y se corrigió el falso positivo del clasificador de greetings.

---

## Novedades desde CP-21B-STABLE

### FASE 22A — Tool Runtime Policies

- `runtime/policies/tools/`: 5 JSONs + policy_loader + manifest
- 3 modos: `disabled` (strip all), `readonly` (allowed_names filter), `agentic` (preserve)
- `blocked_tools.json` como lista maestra global
- Integrado en `apply_profile()` — un solo punto de enforcement

### FASE 22B — Tool Execution Safety

- **Bash sanitizer**: `shlex.split()` token scanning. Pipes, redirects, `&&`, `||` bloqueados por modo
- **Confirmation gate**: 428 Precondition Required para herramientas de escritura
- **Auditoría**: `tool_call_allowed` / `tool_call_blocked_by_policy` por tool individual
- **Presupuesto**: `_tool_budget_exceeded`, `_tool_budget_original`, `_tool_budget_limit`
- **Métricas**: `ailab_tool_call_total{tool_name, result, policy, mode}`

### FASE 22B.1 — Classifier Precision Patch

- `is_greeting_request()`: word-boundary token matching en vez de substring
- "escribe", "history", "this" ya no son falsos greetings

---

## Arquitectura de tools

```
apply_profile()
  └─ apply_tool_policy()
       ├─ blocked_tools.json (master)
       ├─ policy blocked_names + allowed_names (filter)
       ├─ bash_sanitizer (shlex.split)
       ├─ budget enforcement (max_tool_calls)
       ├─ audit per tool_call
       └─ metrics (Prometheus)

do_POST() [gateway]
  └─ confirmation gate (428)
       └─ tool_call_is_dangerous() [firewall final]
```

---

## Perfiles cognitivos (sin cambios desde 21B)

| Perfil | Modelo | max_tokens | Tools | Ruta |
|--------|--------|------------|-------|------|
| chat | qwen2.5-14b | 512 | disabled | fast, general |
| coding | qwen2.5-14b | 1024 | readonly | coding |
| analysis | qwen2.5-32b | 2048 | disabled | reasoning |
| observe | llama-3.1-8b | 256/96 | disabled | minimal, casual, greet, observe |
| agent | qwen3.6-27b | 2048 | agentic | tool_use, tool_fastpath |

---

## Métricas (Prometheus)

| Métrica | Labels |
|---------|--------|
| `ailab_route_family_total` | `family` |
| `ailab_profile_total` | `profile, route_family, model` |
| `ailab_tool_call_total` | `tool_name, result, policy, mode` |
| `ailab_governance_blocked_actions_total` | — |
| `ailab_governance_blocked_actions_by_reason_total` | `reason` |

---

## Rollback

```bash
git checkout CP-21B-STABLE
sudo systemctl restart ailab-router ailab-gateway
```

---

## Capas del runtime

```
Prompts       → lenguaje          ✅ (20C)
Profiles      → comportamiento    ✅ (21A)
Policies      → permisos          ✅ (22A)
Execution     → enforcement       ✅ (22B)
Models        → inferencia        ✅ (20A)
Routing       → decisión          ✅
Observability → trazabilidad      ✅ (21A.1)
Memory        → contexto          ⏭ (23)
Scheduler     → multi-GPU         ⏭ (25)
```

---

## Commits desde CP-21B-STABLE

```
213cb1fa fix(fase22b.1): is_greeting_request() word-boundary token matching
3fb827ba docs: FASE 22B tool execution safety
86de65b4 feat(fase22b-5): TOOL_CALL_TOTAL metrics
c6633f29 feat(fase22b-4): confirmation gate 428
90b457d6 feat(fase22b-3): bash sanitizer with shlex.split()
81d4aca5 feat(fase22b-2): tool call budget metadata
eb441f35 feat(fase22b-1): audit per tool_call
44593631 docs: FASE 22A tool runtime policies
b51db0e3 feat(fase22a): declarative tool runtime policies
```
