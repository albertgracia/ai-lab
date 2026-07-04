# HERMES-E06: Dynamic Governance

**Estado:** PASS
**Fecha:** 2026-07-04
**HEAD:** (to be committed)

---

## 1. Resumen

Implementación completa de ADR-006 (Dynamic Governance). Sistema de gobiernos declarativos con 4 modos, matrix capability-governance, resolver de señales, anti-flapping y reglas de transición. Cero enforcement, modo declarativo puro.

## 2. Componentes

### `runtime/hermes/governance/modes.json`
4 modos de gobierno: NORMAL, ELEVATED, DEGRADED, LOCKDOWN. Cada modo define:
- `allows` / `blocks` — listas de operaciones permitidas/bloqueadas
- `default_capability_behavior` — comportamiento default para capabilities sin entrada explícita en matrix
- `requires_approval` — operaciones que requieren aprobación explícita

### `runtime/hermes/governance/matrix.json`
Matrix capability-governance: las 6 capabilities mapeadas a cada modo:
- `ai-lab-runtime`: allowed en NORMAL/DEGRADED/LOCKDOWN, requires_approval en ELEVATED
- `marketplace-operator`: blocked en DEGRADED/LOCKDOWN
- `observability`: allowed en NORMAL/ELEVATED/DEGRADED, blocked en LOCKDOWN
- `gitnexus-analysis`: allowed en NORMAL/ELEVATED/DEGRADED, blocked en LOCKDOWN
- `deployment-review`: requires_approval en NORMAL/ELEVATED, blocked en DEGRADED/LOCKDOWN
- `incident-response`: allowed en TODOS los modos

### `runtime/hermes/governance/resolver.py`
- `GovernanceResolver`: clase principal con resolución de modo basada en señales
- `TriggerSignals`: 6 señales (slo_state, degradation_level, emergency_mode, vram_pressure, gpu_pressure, timeout_rate)
- Prioridad de resolución: LOCKDOWN > DEGRADED > ELEVATED > NORMAL
- Anti-flapping: 30s mínimo entre transiciones (configurable)
- Reglas de transición con stabilization periods (LOCKDOWN → cualquier modo requiere intervención manual)
- Resolución de capability status por modo + matrix

### Integración
- `models.py`: GovernanceModeDef, GovernanceState, TriggerSignals, CapabilityGovernanceEntry
- `loader.py`: load_governance_modes(), load_governance_matrix()
- `validation.py`: 3 validadores de governance
- `status.py`: governance_mode y governance_transition_count en JSON output

## 3. Validación de señales

| Señal | Condición → Modo |
|-------|-----------------|
| emergency_mode=true | → LOCKDOWN |
| degradation_level=HEAVY/EMERGENCY | → DEGRADED |
| degradation_level=LIGHT | → ELEVATED |
| slo_state=RED | → ELEVATED |
| vram_pressure>0.9 | → ELEVATED |
| gpu_pressure>0.9 | → ELEVATED |
| timeout_rate>0.1 | → ELEVATED |
| Default | → NORMAL |

## 4. Tests

| Archivo | Tests | Estado |
|---------|-------|--------|
| `test_hermes_enterprise_loader.py` | 27 | ✅ PASS |
| `test_hermes_capability_registry.py` | 24 | ✅ PASS |
| `test_hermes_operator_registry.py` | 17 | ✅ PASS |
| `test_hermes_governance.py` | 45 | ✅ PASS |
| **Total** | **113** | **113/113 PASS** |

## 5. Restricciones cumplidas

- ✅ Sin enforcement activo (enforcement_active=false)
- ✅ Sin dispatch de operadores
- ✅ Sin llamadas MCP
- ✅ Sin tocar Gateway/Router/Marketplace/Prometheus/Grafana
- ✅ 0 errores de validación
- ✅ 0 warnings de governance

## 6. Conclusión

**PASS.** ADR-006 implementado completamente: governance declarativo, resolver dinámico, matrix capability-governance, anti-flapping, reglas de transición, validación cruzada, integración en status report. 45 tests de governance, 113 total PASS.
