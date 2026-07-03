# AI-LAB-ASTRO-PUBLISHING-GUARDRAILS-01

## Resultado: PARTIAL

## Base Git
- HEAD/base: `27c6de79`
- Branch: `main`
- Repo: `/opt/ai-lab`
- Workspace: clean at start aside from the prior Astro worktree state already presente.

## Alcance
- Se crearon guardrails reutilizables para publicaciones Astro.
- No se recupero `/ai-infrastructure` en esta fase.
- No se tocaron `runtime/`, `runtime/state/`, Gateway, Router, MCP runtime, Prometheus, Grafana, Docker ni systemd.

## Archivos creados o modificados
- `apps/ialab-docs/src/styles/global.css`
- `apps/ialab-docs/src/components/visual/VisualSection.astro`
- `apps/ialab-docs/src/components/visual/VisualCard.astro`
- `apps/ialab-docs/src/components/visual/MetricBadge.astro`
- `apps/ialab-docs/src/components/visual/RoadmapBlock.astro`
- `apps/ialab-docs/scripts/validate-astro-visual.mjs`
- `apps/ialab-docs/package.json`
- `apps/ialab-docs/src/content/docs/governance/astro-visual-system.md`

## Guardrails a?adidos
- Clases CSS anti-overflow y tipografia segura.
- Componentes visuales reutilizables con `min-width: 0` y wrapping seguro.
- Script local `validate:visual` para bloquear riesgos visuales.
- Regla operativa documentada: `npm run build` no basta.
- Regla documental: no publicar sin revision visual.

## CSS anti-overflow
- `ai-visual-section`
- `ai-visual-grid`
- `ai-visual-card`
- `ai-visual-card-title`
- `ai-visual-card-kicker`
- `ai-visual-metric`
- `ai-visual-code-badge`
- `ai-visual-callout`
- `ai-visual-roadmap`
- `ai-visual-safe-text`

## Componentes/patrones creados
- `VisualSection.astro`
- `VisualCard.astro`
- `MetricBadge.astro`
- `RoadmapBlock.astro`

## Script de validacion
- `apps/ialab-docs/scripts/validate-astro-visual.mjs`
- Verifica existencia de `dist/ai-infrastructure/index.html`.
- Verifica CSS y componentes visuales base.
- Bloquea metricas largas fuera de badge/code.
- Bloquea frases operativas en ingles en bloques visibles.
- Bloquea cards ad hoc sin `min-width: 0` o sin clases visuales oficiales.

## Resultados de build y validacion
- `npm run build`: PASS
- `npm run validate:visual`: FAIL esperado por regresion visual existente

## Regresion detectada
- `ailab_cognitive_health_score` fuera de badge/code.
- `ai_lab:runtime_health_score` fuera de badge/code.
- `no_nodes_online` fuera de badge/code.
- `google/gemma-4-e4b` fuera de badge/code.
- `qwen/qwen2.5-coder-14b-instruct` fuera de badge/code.
- `card ad hoc sin min-width:0 o clases visuales oficiales`.

## Interpretacion
- El guardrail funciona: no deja pasar una publicacion solo por compilar.
- La regresion actual sigue presente y queda bloqueada para la fase siguiente.

## Restricciones respetadas
- No runtime modificado
- No servicios reiniciados
- No push
- No tag
- No recovery de `/ai-infrastructure` en esta fase

## Siguiente fase obligatoria
- `AI-LAB-ASTRO-AI-INFRASTRUCTURE-RECOVERY-01`
