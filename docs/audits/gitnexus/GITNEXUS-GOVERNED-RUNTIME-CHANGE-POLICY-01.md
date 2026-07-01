# GITNEXUS-GOVERNED-RUNTIME-CHANGE-POLICY-01

## Objetivo
Establecer una politica operativa obligatoria para cualquier cambio en modulos runtime criticos de AI-LAB, con analisis previo de impacto usando GitNexus, clasificacion de riesgo, validacion minima y smoke runtime.

## Base de evidencia
- `runtime/gateway/openai_gateway.py` identificado como chokepoint runtime.
- Impacto observado con GitNexus:
  - `impactedCount: 47`
  - `risk: HIGH`
  - `direct depth-1: 18`
- Simbolo sensible: `inject_agent_context`.
- Relacion de routing: `inject_agent_context` <-> `classify_chat_route`.

## Ambito de modulos criticos
Antes de editar cualquiera de estos targets se debe ejecutar analisis GitNexus previo:

- `runtime/gateway/openai_gateway.py`
- `runtime/gateway/runtime_api_routes.py`
- `runtime/gateway/tool_request_classifier.py`
- `runtime/llm/router_api.py`
- `runtime/health/cognitive_health_layer.py`
- `runtime/control/control_plane.py`
- `runtime/telemetry/prometheus_metrics.py`
- `runtime/correlation/*`
- `runtime/critical_path/*`
- `runtime/hotspot_history/*`
- `runtime/governance_drift/*`
- `runtime/federation/*`
- `runtime/slo/*`
- `runtime/triage/*`

## Politica GitNexus obligatoria (pre-cambio)
Para cambios runtime criticos:

1. Ejecutar `gitnexus_impact` sobre archivo o simbolo objetivo.
2. Ejecutar `gitnexus_context` si el cambio toca simbolos concretos.
3. Ejecutar `gitnexus_query` si se requiere entender flujo de ejecucion.
4. No usar `gitnexus_rename`, `gitnexus_cypher` ni `gitnexus_detect_changes` sin autorizacion humana explicita.

## Clasificacion obligatoria del cambio
Antes de editar, clasificar el cambio en una categoria:

1. Contrato publico (`/v1/chat/completions`, `/v1/models`, `/health`, `/metrics`, `/runtime/*`)
2. Routing / seleccion de modelo
3. Observabilidad / metricas
4. Health / control plane
5. Docs/tests only
6. Internals bounded sin cambio de contrato

Regla por defecto:
- Si toca `runtime/gateway/openai_gateway.py`, asumir `risk=HIGH` salvo evidencia fuerte contraria.

## Formato obligatorio antes de modificar
Antes de cualquier edicion runtime critica, el agente debe producir:

1. `HARD_FACTS`
   - archivo objetivo
   - resultado de `gitnexus_impact`
   - `impactedCount`
   - `risk`
   - dependencias directas
   - simbolos sensibles
   - tests afectados
2. `INFERIDO`
   - blast radius probable
   - riesgos de contrato
   - planos afectados
3. `UNKNOWNS`
   - vacios de procesos/materializacion
   - cobertura incompleta
4. Plan minimo
   - cambio propuesto
   - archivos a tocar
   - validacion must-pass
   - rollback

No editar hasta completar este bloque.

## Must-pass minimo si se toca openai_gateway.py
Ejecutar como minimo:

```bash
python3 -m compileall -q runtime tests
pytest -q tests/test_gateway_openai_contract_39a.py
pytest -q tests/test_gateway_graceful_shutdown_01.py
pytest -q tests/test_model_registry_canonical_01.py
pytest -q tests/test_cognitive_health_layer_37a.py
pytest -q tests/test_parallel_tool_call_hardening.py
```

Si falla cualquier test:
- No cerrar como `STABLE`.
- Explicar causa y clasificar relacionado/no relacionado.

Regla LM Studio:
- `tests/test_lmstudio_contract_01.py` solo puede marcarse no bloqueante si el cambio no toca inventario/model registry/contrato LM Studio y se documenta explicitamente la ausencia de modelo cargado.

## Smoke runtime minimo si se toca gateway

```bash
curl -s http://127.0.0.1:8008/health | jq
curl -s http://127.0.0.1:8008/v1/models | jq
curl -s http://127.0.0.1:8008/runtime/health/summary | jq
curl -s http://127.0.0.1:8008/runtime/correlation/summary | jq
curl -s http://127.0.0.1:8008/runtime/critical-path/summary | jq
curl -s http://127.0.0.1:8008/runtime/hotspot-history/summary | jq
curl -s http://127.0.0.1:8008/runtime/governance-drift/summary | jq
curl -s http://127.0.0.1:8083/health | jq
curl -s http://127.0.0.1:8083/v1/models | jq
```

Si hubo restart de gateway, revisar:

```bash
journalctl -u ailab-gateway -n 120 --no-pager
```

No deben aparecer:
- `stop-sigterm timed out`
- `SIGKILL`
- `Failed with result timeout`
- stacktrace nuevo asociado al cambio

## Reglas de seguridad
No tocar sin orden explicita:

- `runtime/state/*`
- `AGENTS.md`
- `runtime/planner/tool_planner.py`
- `stacks/ai-core/docker-compose.yml`
- `snapshots/*`
- `dist/*`
- `.gitnexus/*`
- `/opt/gitnexus`
- `/usr/local/lib/node_modules`
- systemd / docker-compose / proxy infra

## Regla especial memoria / Qdrant
Tratar como sensibles:

- `runtime/gateway/openai_gateway.py`
- `inject_agent_context`
- `runtime/agent/context_shaper.py`
- `runtime/agent/selective_context.py`
- `runtime/semantic/*`
- `runtime/memory/*`

Antes de tocar inyeccion contextual:
- correr `gitnexus_impact`
- verificar relacion con `classify_chat_route`
- separar factual vs inferido vs unknown
- no inyectar payload crudo sin gobernanza
- no persistir prompts sin politica explicita

## Criterio de cierre STABLE (runtime critico)
Una fase runtime critica solo cierra como `STABLE` si tiene:

1. GitNexus impact previo
2. HARD_FACTS / INFERIDO / UNKNOWNS
3. cambio minimo
4. tests must-pass
5. smoke runtime
6. rollback claro
7. commit limpio
8. tag estable
9. worktree dirty restante identificado

## Plantilla de salida obligatoria
Toda fase runtime critica debe cerrar con:

- Resultado: `PASS | PARTIAL | FAIL | BLOCKED`
- GitNexus impact usado: `si/no`
- Archivos tocados
- Riesgo GitNexus
- Tests ejecutados
- Smoke ejecutado
- Riesgos
- Rollback
- Commit
- Tag
- Worktree dirty restante

Si no se usa GitNexus en un cambio runtime critico, debe justificarse explicitamente.
