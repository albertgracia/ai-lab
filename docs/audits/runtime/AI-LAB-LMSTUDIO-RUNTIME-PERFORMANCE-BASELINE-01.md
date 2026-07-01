# AI-LAB-LMSTUDIO-RUNTIME-PERFORMANCE-BASELINE-01

## Resultado: PASS

## Git state
- HEAD/base: eeefb720
- Branch: main
- Status start: clean, synced with origin/main
- No push, no tag, no rebase

## Runtime state
- Gateway: ok, backend http://192.168.1.50:1234/v1
- Runtime health: healthy, score 89.6
- Nodes online: 2
- Routing confidence: 0.89
- Grounding: ok, grounded=false, confidence=low
- Router: ok

## OpenAI-compatible endpoints
- Gateway /v1/models: available
- Router /v1/models: available
- Gateway models observed: qwen3-vl-8b-instruct, qwen/qwen2.5-coder-14b-instruct, text-embedding-nomic-embed-text-v1.5, google/gemma-4-e4b, qwen2.5-coder-14b-instruct
- Router models observed: ailab-router/auto, ailab-router/fast, ailab-router/reasoning, ailab-router/coding

## Benchmark method
- Principal endpoint: http://127.0.0.1:8008/v1/chat/completions
- Request model: google/gemma-4-e4b
- Returned model: qwen3-vl-8b-instruct
- Prompts were neutral to avoid diagnostic fast-path responses
- Streaming was not used

## Gateway results

| test | model | latencia_s | prompt_tokens | completion_tokens | total_tokens | tokens/s | finish_reason |
|---|---|---:|---:|---:|---:|---:|---|
| sky_blue | qwen3-vl-8b-instruct | 10.500 | 113 | 109 | 222 | 10.38 | stop |
| tea_hot | qwen3-vl-8b-instruct | 10.110 | 116 | 109 | 225 | 10.78 | stop |
| maps_route | qwen3-vl-8b-instruct | 8.473 | 121 | 85 | 206 | 10.03 | stop |

### Gateway summary
- tokens/s avg: 10.40
- tokens/s min: 10.03
- tokens/s max: 10.78
- all 3 requests succeeded

## Router comparison sample
- Endpoint: http://127.0.0.1:8083/v1/chat/completions
- Model: ailab-router/fast
- Returned model: qwen/qwen2.5-coder-14b-instruct
- Latency: 42.981s
- prompt_tokens: 891
- completion_tokens: 120
- tokens/s: 2.79
- finish_reason: length

## Prometheus state
- ailab_cognitive_health_score = 86.8
- ailab_cognitive_health_nodes_online = 3
- ailab_cognitive_health_routing_confidence = 0.87
- rate(ailab_gateway_requests_total[5m]): no series returned

## Logs
- Gateway logs: recent BrokenPipeError entries only
- Router logs: no recent errors matched the filter

## Interpretation
- Gateway baseline is stable but materially below the operator informal 30-50 tokens/s observation.
- The measured gateway throughput is around 10 tps on neutral prompts with the selected route.
- Router path is slower in this sample and carries substantial prompt inflation.

## Limitations
- Non-streaming completions only
- One router sample only
- Throughput varies with route selection and prompt shape

## Recommendation
- Next phase: AI-LAB-ROUTER-AUTO-DIAGNOSTIC-01
- Alternative follow-up: AI-LAB-LMSTUDIO-NODE-PROFILES-01

## Constraints respected
- No runtime modified
- No services restarted
- No configuration changed
- No push
- No tag
