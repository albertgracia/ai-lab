# AI-LAB-LMSTUDIO-STREAMING-VS-NONSTREAMING-BENCHMARK-PUSH-01

## Resultado: PASS

## HEAD inicial
- 3f313ee5 docs(audit): benchmark lmstudio streaming versus nonstreaming

## HEAD final
- 3f313ee5 docs(audit): benchmark lmstudio streaming versus nonstreaming

## Commit pusheado
- 3f313ee5 docs(audit): benchmark lmstudio streaming versus nonstreaming

## Merge
- No hubo merge adicional

## Confirmaciones
- Push principal realizado
- Branch sincronizada con origin/main
- Working tree limpio
- No tag en HEAD
- No runtime tocado
- No servicios tocados

## Resumen benchmark
- Non-streaming avg: 6.19 tps
- Streaming avg estimado: 4.20 tps
- Streaming TTFB avg: 28.401s
- Gateway non-streaming: 3.08 / 11.17 tps
- Gateway streaming: 2.49 / 5.90 tps
- Router non-streaming sample: 3.59 tps
- Router gemma non-streaming: 11.17 tps

## Modelos devueltos
- Gateway auto: qwen/qwen2.5-coder-14b-instruct
- Gateway gemma: qwen3-vl-8b-instruct
- Router auto: qwen/qwen2.5-coder-14b-instruct
- Router gemma: google/gemma-4-e4b

## Interpretación
- Streaming expone TTFB, pero no mejoró throughput en esta muestra.
- Router añade overhead en auto routing.
- Gateway no preserva siempre el modelo solicitado.
- ilab-router/auto preservó Gemma en la muestra Router streaming.

## Riesgo residual
- Streaming parcial en Router por pocos chunks/sin usage.
- TTFB alto.
- Gateway no preserva modelo explícito.

## Siguiente fase
- AI-LAB-ROUTER-AUTO-DIAGNOSTIC-01
