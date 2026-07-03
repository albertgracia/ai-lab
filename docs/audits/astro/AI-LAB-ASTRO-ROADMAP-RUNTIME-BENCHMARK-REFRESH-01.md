# AI-LAB-ASTRO-ROADMAP-RUNTIME-BENCHMARK-REFRESH-01

## Resultado: PASS

## Base Git
- HEAD/base: 8cdd61de
- Branch: main
- Repo: /opt/ai-lab
- Workspace: clean at start

## Archivo actualizado
- apps/ialab-docs/src/pages/ai-infrastructure/index.astro

## Ruta validada
- /ai-infrastructure

## Resumen de cambios Astro
- Se actualizo la pagina con un hero ejecutivo y cards de estado.
- Se separo claramente Runtime/Cognitive Health y Infra/SLO Cross-check.
- Se reflejo la semantica de Grafana para Health Drift e Inference Nodes Online.
- Se incorporaron los benchmarks reales de LM Studio, Gateway y Router.
- Se actualizo la seccion de Router Auto con la lectura source-backed.
- Se aclaro que ailab_route_preview es una tool MCP local heuristica, no un endpoint HTTP del router.
- Se dejo un roadmap corto y visual para las proximas fases.

## Benchmarks incorporados
- Gateway baseline: 10.40 tps
- Gateway range: 10.03 / 10.78 tps
- Streaming benchmark: 6.19 tps non-streaming avg
- Streaming estimated: 4.20 tps
- Streaming TTFB avg: 28.401s
- Router Gemma non-streaming: 11.17 tps
- Router sample: 2.79 tps
- Nota incluida: la UI de LM Studio no es comparable con el end-to-end API

## Router Auto incorporado
- ailab-router/auto mapea por defecto a qwen/qwen2.5-coder-14b-instruct en la policy.
- choose_model() rankea por capability, performance y health.
- router_api usa capability_from_model() solo para /fast, /reasoning y /coding.
- ailab-router/auto no tiene override especial para Gemma.
- Router preserva google/gemma-4-e4b cuando se pide explicitamente.
- Streaming y non-streaming comparten la seleccion inicial.

## MCP Tools aclaradas
- ailab_status
- ailab_runtime_health
- ailab_route_preview
- ailab_route_preview queda descrita como tool local heuristica, no endpoint HTTP.

## Roadmap actualizado
### Proximo bloque recomendado
- AI-LAB-LMSTUDIO-NODE-PROFILES-01

### Fases para manana
- AI-LAB-LMSTUDIO-NODE-PROFILES-01
- AI-LAB-ROUTER-AUTO-POLICY-TRACEABILITY-01
- AI-LAB-MCP-TOOLS-CATALOG-VALIDATION-01
- AI-LAB-GATEWAY-MODEL-PRESERVATION-POLICY-01
- AI-LAB-ASTRO-ROADMAP-REFRESH-NEXT-01

### Pendientes en reserva
- AILAB_MCP_TOKEN + LAN controlled mode
- Tools semanticas reales: sommelier, analyze_label, price_estimate
- Rioja Marketplace integration
- Multi-GPU runtime scheduler
- Hyper-V checkpoint

## Build Astro
- npm run build: PASS
- Paginas generadas: 259
- Ruta dist validada: dist/ai-infrastructure/index.html

## Validacion de secretos
- No se detectaron secretos en la pagina compilada.
- AILAB_MCP_TOKEN solo aparece como nombre de variable, sin valor real.

## Restricciones respetadas
- No runtime modificado
- No servicios reiniciados
- No configuracion tocada
- No push
- No tag
