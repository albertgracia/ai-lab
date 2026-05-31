# AI-LAB-ROUTER-AUTO-DIAGNOSTIC-01

## Resultado: PASS

## Scope
- Diagnose how ailab-router/auto resolves model choice.
- Compare auto routing with explicit model requests.
- Confirm whether route preview or explanation exists.

## Preflight
- Repo: /opt/ai-lab
- Branch: main
- HEAD/base: 57fba7da
- Working tree: clean at start

## Runtime snapshot
- Gateway: ok, backend http://192.168.1.50:1234/v1
- Runtime health: 86.8
- Nodes online: 3
- Routing confidence: 0.87
- Router: ok

## Source inspection recovery

### Files inspected
- runtime/models/model_policy.py
- runtime/router/model_policy.py
- runtime/router/capability_router.py
- runtime/llm/router_api.py
- runtime/gateway/openai_gateway.py
- mcp/servers/ailab_semantic_gateway.py
- tests/test_router_model_policy_01.py
- tests/test_mcp_semantic_gateway_01.py

### Regla de seleccion encontrada

La regla canonica de rutas esta en runtime/models/model_policy.py:

- auto -> qwen/qwen2.5-coder-14b-instruct
- fast, observe, minimal, fallback, degraded, greeting, lightweight -> qwen3-vl-8b-instruct
- coding, reasoning, tool-use, architecture, report -> qwen/qwen2.5-coder-14b-instruct

runtime/router/model_policy.py es solo un adaptador de compatibilidad y preserva la misma tabla canonica.

### Como decide el router real

runtime/router/capability_router.py::choose_model(task_type) hace el ranking real:

- usa discovery + registry cuando estan disponibles
- filtra candidatos por capacidad (tool_use, coding, reasoning, etc.)
- combina capability score, task match, performance, disponibilidad, speed y health
- cae a fallback estatico si no hay candidatos

### Como resuelve /v1/chat/completions

runtime/llm/router_api.py no trata ailab-router/auto como una ruta especial de preservacion:

- capability_from_model() solo reconoce sufijos /fast, /reasoning, /coding
- si el modelo pedido es ailab-router/auto, la capability queda None
- luego select_node(request_text, capability=effective_capability) elige nodo/modelo por texto + capability
- el payload upstream usa el modelo seleccionado del nodo
- en streaming y non-streaming la seleccion previa es la misma; cambia la rama de transporte, no la decision inicial

### OpenAI gateway

runtime/gateway/openai_gateway.py usa la misma idea:

- selected_model = choose_model(task_type)
- el stream solo cambia el transporte hacia LM Studio
- la rama de respuesta no vuelve a elegir modelo
- el override posterior de modelo pedido solo contempla qwen/qwen2.5-coder-14b-instruct y qwen3-vl-8b-instruct
- no hay override especial para google/gemma-4-e4b

## Observed behavior

| test | endpoint | model requested | model returned | stream | elapsed_s | ttfb_s | completion_tokens | est_completion_tokens | tps | chunks | finish_reason | error |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| router_auto_nonstream | Router | ailab-router/auto | qwen/qwen2.5-coder-14b-instruct | no | 72.382 | N/A | 260 | N/A | 3.59 | N/A | length | none |
| router_auto_stream | Router | ailab-router/auto | google/gemma-4-e4b | yes | 23.348 | 23.348 | N/A | N/A | N/A | 2 | length | none |
| router_gemma_nonstream | Router | google/gemma-4-e4b | google/gemma-4-e4b | no | 23.269 | N/A | 260 | N/A | 11.17 | N/A | length | none |
| router_gemma_stream | Router | google/gemma-4-e4b | google/gemma-4-e4b | yes | 23.138 | 23.138 | N/A | N/A | N/A | 2 | length | none |

## Why stream and non-stream can differ
- The router and gateway selection step happens before the stream branch.
- The stream branch wraps upstream SSE and uses the model field from the upstream response.
- The non-stream branch sanitizes the JSON response but does not rewrite model.
- So the returned model can drift because the upstream/backend response differs by transport, not because the router re-runs selection.

## Why explicit Gemma can appear preserved
- The Router has no Gemma-specific preservation rule.
- capability_from_model() does not recognize Gemma IDs.
- The observed Gemma return is therefore a selection outcome or backend response, not a hardcoded preservation path.
- In other words: google/gemma-4-e4b can survive, but it is not guaranteed by policy.

## Route preview or explanation
- No dedicated router HTTP endpoint for route preview or explanation was confirmed.
- ailab_route_preview exists as a local MCP tool in mcp/servers/ailab_semantic_gateway.py.
- It is heuristic-only and explicitly does not call a model.
- Tests confirm the tool returns route_family, confidence, and reason without LLM inference.

## Conclusion
- ailab-router/auto is canonically mapped to the coder model in policy.
- The live router selection is capability-aware and prompt-driven.
- Streaming vs non-streaming share the same selection step, but the returned model can differ because the backend response model is preserved differently.
- The earlier PARTIAL status is resolved by direct source inspection.

## Validation
- venv pytest passed for tests/test_router_model_policy_01.py and tests/test_mcp_semantic_gateway_01.py
- Result: 43 passed

## Constraints respected
- No runtime modified
- No services restarted
- No config changed
- No push
- No tag
