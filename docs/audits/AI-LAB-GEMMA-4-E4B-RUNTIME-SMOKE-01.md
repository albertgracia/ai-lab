# AI-LAB-GEMMA-4-E4B-RUNTIME-SMOKE-01

## Resultado: PASS

## Git state
- HEAD/base: ebef7005
- Branch: main
- Status start: clean, synced with origin/main
- No push, no tag, no rebase

## Runtime state
- Gateway: ok, backend http://192.168.1.50:1234/v1
- Runtime health: healthy, score 92.4
- Nodes online: 3
- Routing confidence: 0.91
- Grounding: ok, grounded=false, confidence=low
- Router: ok

## Model availability
- Gateway models list includes google/gemma-4-e4b
- Router models list is available

## Smoke method
- Requested model: google/gemma-4-e4b
- Gateway endpoint: http://127.0.0.1:8008/v1/chat/completions
- Router endpoint: http://127.0.0.1:8083/v1/chat/completions

## Gateway smoke

| test | model_requested | model_returned | latencia_s | prompt_tokens | completion_tokens | total_tokens | tps | finish_reason |
|---|---|---|---:|---:|---:|---:|---:|---|
| sky_blue | google/gemma-4-e4b | qwen3-vl-8b-instruct | 14.558 | 118 | 147 | 265 | 10.10 | stop |
| tea_hot | google/gemma-4-e4b | qwen3-vl-8b-instruct | 10.635 | 121 | 107 | 228 | 10.06 | stop |
| photosynthesis | google/gemma-4-e4b | qwen3-vl-8b-instruct | 9.023 | 119 | 95 | 214 | 10.53 | stop |

### Gateway summary
- tokens/s avg: 10.23
- tokens/s min: 10.06
- tokens/s max: 10.53
- all 3 neutral requests succeeded

### Prompt-sensitive behavior observed
- Some operational prompts triggered diagnostic-style responses or a different effective model path
- One coding-oriented prompt returned qwen/qwen2.5-coder-14b-instruct at 4.83 tps
- This suggests prompt shape can change the effective route/model even when google/gemma-4-e4b is requested

## Router smoke
- Requested model: google/gemma-4-e4b
- Returned model: google/gemma-4-e4b
- Latency: 35.756s
- completion_tokens: 180
- tps: 5.03
- finish_reason: length

## Logs
- Gateway logs: route/profile lines for google/gemma-4-e4b, no critical errors in the filtered sample
- Router logs: a matching profile line, no critical errors in the filtered sample

## Comparison with baseline
- Previous Gateway baseline: 10.40 tps
- Previous Router sample: 2.79 tps
- This smoke is consistent with the prior Gateway baseline and faster than the earlier Router sample

## Interpretation
- google/gemma-4-e4b is exposed in Gateway and works in smoke conditions
- The effective model on Gateway neutral prompts was qwen3-vl-8b-instruct, not the requested Gemma ID
- Router passed through Gemma as requested in the smoke sample

## Recommendation
- Good candidate for controlled testing
- Keep it as a usable runtime option, but open a follow-up on routing/model policy if the requested Gemma ID must be preserved end-to-end
- Next phase: AI-LAB-ROUTER-AUTO-DIAGNOSTIC-01

## Constraints respected
- No runtime modified
- No services restarted
- No configuration changed
- No push
- No tag
