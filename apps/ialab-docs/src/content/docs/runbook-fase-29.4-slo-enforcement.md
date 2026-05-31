---
title: "Runbook — FASE 29.4 SLO Enforcement & Adaptive Runtime Protection"
summary: "Runbook operativo para verificar, diagnosticar y actuar sobre el SLO enforcement runtime. Incluye queries rapidas, interpretacion de estados, procedimientos de dry-run a enforcement activo, y troubleshooting de metricas."
order: 79
---

## Objetivo

Operar el SLO enforcement runtime de AI-LAB: verificar estado, interpretar degradaciones, activar/desactivar enforcement, y diagnosticar metricas flatlineadas o transiciones incorrectas.

## Vista rapida

```bash
# Estado SLO completo
curl -s http://192.168.1.30:8008/slo/health | jq .

# Metricas clave
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_slo"
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_degradation"
curl -s http://192.168.1.30:8008/metrics | grep "ailab_slo_violations"

# Dashboard
# https://192.168.1.40:3000/d/ailab-runtime-protection
```

## Estados SLO

| Codigo | Nombre | Color | Significado |
|--------|--------|-------|-------------|
| 0 | GREEN | Verde | Todos los SLOs dentro de target. Operacion normal. |
| 1 | YELLOW | Amarillo | 1+ SLO en warning. Degradacion LIGHT activa (si enforcement ON). |
| 2 | RED | Rojo | 1+ SLO en critical. Degradacion HEAVY/EMERGENCY (si enforcement ON). |

### Que hacer en cada estado

**GREEN**: monitoreo normal. No requiere accion.

**YELLOW**: revisar que SLO esta en warning:
```bash
curl -s http://192.168.1.30:8008/slo/health | jq '.violations[] | select(.level=="warning")'
```
Causas tipicas: GPU>85% temporal, TTFB p50>800ms por cold start, pico de requests.

**RED**: identificar que SLO esta en critical:
```bash
curl -s http://192.168.1.30:8008/slo/health | jq '.violations[] | select(.level=="critical")'
```
Causas tipicas: GPU>95% sostenido, timeout rate>5%, VRAM>97%, gateway crash o orphan stream.

## Niveles de Degradacion

| Level | Nombre | Que protege | Como diagnosticar |
|-------|--------|-------------|-------------------|
| 0 | NORMAL | — | `ailab_runtime_degradation_level == 0` |
| 1 | LIGHT | qwen, TTFB | `ailab_runtime_degradation_level == 1`. Forced llama activo. |
| 2 | HEAVY | VRAM, estabilidad | No auto-activo. Observable via metrica. |
| 3 | EMERGENCY | gateway, streams | No auto-activo. Observable via metrica. |

### Ver protecciones activas

```bash
# Forced llama routing events
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_llama_fastpath_forced_total"

# Qwen protection events
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_qwen_protection_total"

# Emergency activations
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_emergency_mode_total"

# Concurrencia dinamica actual
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_qwen_parallel"
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_concurrent_streams"
```

## Feature Flags

```bash
# Ver estado actual
echo "SLO_DRY_RUN=${AI_LAB_SLO_DRY_RUN:-true}"
echo "SLO_ENFORCEMENT=${AI_LAB_ENABLE_SLO_ENFORCEMENT:-false}"

# Para activar enforcement real (tras validar dry-run):
export AI_LAB_SLO_DRY_RUN=false
export AI_LAB_ENABLE_SLO_ENFORCEMENT=true
# Requiere reinicio del gateway: sudo systemctl restart ailab-gateway

# Para desactivar (rollback inmediato):
export AI_LAB_ENABLE_SLO_ENFORCEMENT=false
# Sin reinicio: solo afecta a nuevos requests, no requiere restart
```

## Procedimiento: Pasar de DRY RUN a ENFORCEMENT

1. **Verificar metricas en dry-run** (15 min minimo):
   ```bash
   curl -s http://192.168.1.30:8008/slo/health | jq .
   ```
   Confirmar que `ailab_runtime_slo_state`, `ailab_runtime_degradation_level` aparecen en `/metrics` con valores correctos.

2. **Validar dashboard**: abrir AI-LAB Runtime Protection en Grafana. Confirmar que los 14 paneles muestran datos.

3. **Forzar transicion YELLOW** (opcional, para validar):
   Generar suficiente carga para que GPU suba >85%. Verificar que `ailab_runtime_slo_state` cambia a 1.

4. **Activar enforcement**:
   ```bash
   sudo systemctl set-environment AI_LAB_SLO_DRY_RUN=false
   sudo systemctl set-environment AI_LAB_ENABLE_SLO_ENFORCEMENT=true
   sudo systemctl restart ailab-gateway
   ```

5. **Verificar enforcement activo**:
   ```bash
   curl -s http://192.168.1.30:8008/slo/health | jq '{dry_run, enabled, slo_state, degradation_level}'
   ```
   `dry_run` debe ser `false`, `enabled` debe ser `true`.

6. **Burn-in 30 min**: ejecutar 3 workers concurrentes, verificar:
   - Degradacion LEVEL 1 se activa/desactiva segun carga
   - 0 crashes, 0 orphan streams
   - TTFB se mantiene dentro de SLO targets

## Procedimiento: Rollback

Si el enforcement causa problemas:

1. **Desactivar enforcement** (no requiere restart):
   ```bash
   export AI_LAB_ENABLE_SLO_ENFORCEMENT=false
   ```
   Esto solo afecta a nuevos requests. Las conexiones activas no se interrumpen.

2. **Rollback completo a dry-run**:
   ```bash
   sudo systemctl set-environment AI_LAB_SLO_DRY_RUN=true
   sudo systemctl set-environment AI_LAB_ENABLE_SLO_ENFORCEMENT=false
   sudo systemctl restart ailab-gateway
   ```

3. **Verificar rollback**:
   ```bash
   curl -s http://192.168.1.30:8008/slo/health | jq '{dry_run, enabled, degradation_level}'
   ```
   `dry_run=true`, `enabled=false`, `degradation_level=0`.

## Troubleshooting

### Problema: `ailab_runtime_*` metricas no aparecen en /metrics

Causa: `runtime/slo/` no se importa correctamente.

Diagnostico:
```bash
curl -s http://192.168.1.30:8008/slo/health
```
Si devuelve `{"error": "slo_module_unavailable"}`, el modulo no cargo.

Causas posibles:
- `prometheus_client` no instalado en el venv
- Error de import en `runtime/slo/metrics.py`
- `runtime/slo/__init__.py` lanza excepcion

Fix: verificar el venv:
```bash
/opt/ai-lab/.venv/bin/pip list | grep prometheus_client
python3 -c "from runtime.slo import RuntimeSLOManager; print('OK')"
```

### Problema: degradation_level siempre 0 incluso con GPU>95%

Causa: dry-run mode activo o SLO enforcement desactivado.

Verificar:
```bash
curl -s http://192.168.1.30:8008/slo/health | jq '{dry_run, enabled}'
```

Si `dry_run=true`, el `DegradationManager` evalua y logea pero NO cambia metrica ni actua. Esperado.

Si `enabled=false`, el enforcement entero esta desactivado. Esperado hasta activacion manual.

### Problema: Transiciones SLO demasiado rapidas (flapping)

El `DegradationManager` tiene anti-flapping explicito: minimo 30s entre transiciones de nivel. Si ves transiciones rapidas (>1 cada 30s), hay un bug.

Diagnostico:
```bash
# Ver cambios en degradation_level
curl -s http://192.168.1.30:8008/metrics | grep "ailab_runtime_degradation_level"
```
Si cambia mas de una vez cada 30s, revisar `runtime/slo/degradation.py` → `MIN_TRANSITION_INTERVAL`.

### Problema: Circuit breaker se abre pero requests siguen yendo al modelo

Esperado. En esta fase los circuit breakers son **observables solamente**. No bloquean requests. La metrica `ailab_circuit_breaker_state` expone el estado (0=closed, 1=half, 2=open) pero `should_allow()` siempre retorna `True`.

Si se requiere bloqueo real en una emergencia, usar el degradation manager (LEVEL 3) que fuerza llama-only via gateway.

### Problema: Concurrencia dinamica no cambia

Verificar que `AdaptiveConcurrency.update()` se llama en cada request. Si el gateway no reporta GPU util (siempre 0.0), el concurrency no se adapta.

```bash
curl -s http://192.168.1.30:8008/slo/health | jq '.snapshot.gpu_util'
```
Si es 0.0 constantemente, el gateway no esta reportando GPU state. Revisar `GPU_ACTIVE_REQUESTS` en el gateway.

### Problema: Priority lanes no funcionan (Lane 1 no tiene prioridad)

Los priority lanes actualmente son **slots reservados** en `stream_sanitizer.py`, no una cola de prioridad real. Lane 1 tiene 2 slots dedicados, pero si esos slots estan libres y hay requests de Lane 2, estos pueden ocuparlos.

Para que Lane 1 tenga prioridad real, `PrioritySlotManager.acquire_slot("critical")` debe ser llamado explicitamente desde el gateway antes de iniciar el stream. Verificar que el gateway lo usa.

## PromQL Queries Rapidas

### Estado SLO actual
```promql
ailab_runtime_slo_state
```

### Nivel de degradacion
```promql
ailab_runtime_degradation_level
```

### Tasa de violaciones SLO
```promql
rate(ailab_slo_violations_total[5m])
```

### Presion GPU (ultimos 5 min)
```promql
avg_over_time(ailab_runtime_gpu_pressure[5m])
```

### Eventos de proteccion a qwen
```promql
rate(ailab_runtime_qwen_protection_total[5m])
```

### Llama forzado por degradacion
```promql
rate(ailab_runtime_llama_fastpath_forced_total[5m])
```

### Distribucion de priority lanes
```promql
rate(ailab_runtime_priority_lane_total[5m])
```

### Circuit breaker state actual
```promql
ailab_circuit_breaker_state
```

### Stream backlog actual
```promql
ailab_runtime_stream_backlog
```

## Alertas Sugeridas

### SLO State RED
```promql
ailab_runtime_slo_state >= 2
```
Severidad: critical. El runtime esta degradado. Revisar dashboard AI-LAB Runtime Protection.

### Degradation Level > 0
```promql
ailab_runtime_degradation_level > 0
```
Severidad: warning. El enforcement esta activo. Revisar causas en `ailab_slo_violations_total`.

### Emergency Mode
```promql
increase(ailab_runtime_emergency_mode_total[5m]) > 0
```
Severidad: critical. Emergency mode se activo. Revisar `ailab_runtime_emergency_mode_total{reason=~".*"}`.

### Qwen Protection Spam
```promql
rate(ailab_runtime_qwen_protection_total[5m]) > 1
```
Severidad: warning. Mas de 1 proteccion a qwen por segundo — posible escalation loop.

### SLO Violations Acumuladas
```promql
increase(ailab_slo_violations_total[10m]) > 10
```
Severidad: warning. Muchas violaciones de SLO en ventana de 10 min.

## Referencias

- Codigo: `/opt/ai-lab/runtime/slo/`
- Dashboard: `/opt/ai-lab/dashboards/ailab-runtime-protection.json`
- Documentacion: `historical/phases/fase-29.4-slo-enforcement.md`
- Gateway: `/opt/ai-lab/runtime/gateway/openai_gateway.py` (buscar `_HAVE_SLO` y `FASE 29.4`)
- Stream sanitizer: `/opt/ai-lab/runtime/gateway/stream_sanitizer.py` (buscar `set_max_streams`)
