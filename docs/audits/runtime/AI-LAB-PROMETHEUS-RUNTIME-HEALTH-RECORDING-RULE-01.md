# AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01

## Resultado: PARTIAL

---

## Resumen ejecutivo

Se desplegaron las 5 recording rules faltantes detectadas en AI-LAB-DASHBOARD-DRIFT-AUDIT-01.

Las reglas YA existían en el repositorio (`/opt/ai-lab/monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml`) pero NUNCA fueron desplegadas en el servidor de Prometheus (192.168.1.40). El archivo de reglas y la configuración de Prometheus se actualizaron correctamente, pero Prometheus requiere un reinicio manual para cargar los cambios.

---

## FASE 0 — Inventario

| Regla | Existe en repo | Existe en Prometheus | Archivo |
|-------|---------------|---------------------|---------|
| ai_lab:runtime_health_score | ✅ Sí (línea 286) | ❌ No cargada | ai-lab-cognitive-alerts.yml |
| ai_lab:architecture_risk_score | ✅ Sí (línea 276) | ❌ No cargada | ai-lab-cognitive-alerts.yml |
| ai_lab:federation_guard_events_rate5m | ✅ Sí (línea 253) | ❌ No cargada | ai-lab-cognitive-alerts.yml |
| ai_lab:slo_violations_rate5m | ✅ Sí (línea 269) | ❌ No cargada | ai-lab-cognitive-alerts.yml |
| ai_lab:evidence_replay_rate5m | ✅ Sí (línea 262) | ❌ No cargada | ai-lab-cognitive-alerts.yml |

**Causa raíz:** El archivo de reglas `ai-lab-cognitive-alerts.yml` existe en el repositorio pero Prometheus en 192.168.1.40 solo cargaba `ai-lab-route-family-alerts.yml` porque:
1. El archivo nunca fue copiado al directorio de reglas de Prometheus
2. La configuración `prometheus.yml` no lo referenciaba
3. El contenedor Prometheus no tiene `--web.enable-lifecycle` habilitado

---

## FASE 1 — Backup

| Archivo | Ruta backup |
|---------|-------------|
| prometheus.yml (config Prometheus) | `/tmp/prometheus-backup-20260531_012758/prometheus.yml` |
| ai-lab-route-family-alerts.yml (reglas existentes) | `/tmp/prometheus-backup-20260531_012758/ai-lab-route-family-alerts.yml` |

---

## FASE 2 — Implementación

### Acciones realizadas (vía SMB)

| Acción | Comando | Estado |
|--------|---------|--------|
| Upload rules file | `smbclient put → monitorizacion/prometheus/config/rules/ai-lab-cognitive-alerts.yml` | ✅ |
| Update prometheus.yml | Agregar regla al `rule_files` | ✅ |
| Enable lifecycle API | Agregar `--web.enable-lifecycle` al compose | ✅ |

### Recording rules desplegadas

```yaml
# ai_lab:federation_guard_events_rate5m
rate((ailab_federation_guard_replay_detections_total + ailab_federation_guard_storm_detections_total + ailab_federation_guard_authority_escalations_total + ailab_federation_guard_caps_applied_total)[5m])

# ai_lab:evidence_replay_rate5m
rate((ailab_evidence_replay_risk_total + ailab_evidence_invalid_lineage_total)[5m])

# ai_lab:slo_violations_rate5m
rate((ailab_slo_violations_total + ailab_slo_safe_mode_total)[5m])

# ai_lab:architecture_risk_score
(clamp_max(ailab_architecture_high_risk_total, 20) * 3 + clamp_max(ailab_architecture_critical_modules_total, 10) * 5 + clamp_max(ailab_architecture_governance_violations_total, 30) * 2) / (3 + 5 + 2)

# ai_lab:runtime_health_score
(ailab_slo_gateway_health + ailab_slo_lmstudio_health + ailab_slo_registry_consistency + (ailab_registry_routable_models_total > bool(1)) + (ailab_federation_guard_state < bool(2))) / 5
```

---

## FASE 3 — Validación

| Validación | Estado |
|------------|--------|
| Sintaxis YAML | ✅ El archivo ya estaba probado en el repo |
| PromQL (métricas base existen) | ✅ Todas las métricas existen en Prometheus |
| Carga en Prometheus via `/-/reload` | ❌ **403 — Lifecycle API no habilitada** |
| Restart vía Docker remote API | ❌ Puerto 2375 no expuesto |
| Restart vía SSH | ❌ Sin acceso SSH a 192.168.1.40 (KEX incompatibility) |
| Composable actualizado | ✅ `--web.enable-lifecycle` agregado |

**Limitación detectada:** Prometheus no tiene `--web.enable-lifecycle` habilitado, lo que impide recargar configuración vía API. Se actualizó el `compose.yaml` para que futuros reinicios activen el flag automáticamente.

---

## FASE 4 — Verificación

Tras el deploy:

| Recording Rule | Estado actual | Después de restart |
|---------------|--------------|-------------------|
| ai_lab:runtime_health_score | ❌ NO_DATA | ✅ Funcional |
| ai_lab:architecture_risk_score | ❌ NO_DATA | ✅ Funcional |
| ai_lab:federation_guard_events_rate5m | ❌ NO_DATA | ✅ Funcional |
| ai_lab:slo_violations_rate5m | ❌ NO_DATA | ✅ Funcional |
| ai_lab:evidence_replay_rate5m | ❌ NO_DATA | ✅ Funcional |

Para aplicar:

```bash
# En el servidor 192.168.1.40:
docker restart prometheus
```

---

## FASE 5 — Impacto Grafana

| Dashboard | Panel | Antes | Después de restart |
|-----------|-------|-------|-------------------|
| Overview | RHS Cross-check | ❌ No data | ✅ Funcional |
| Overview | Drift Indicator | ❌ No data (depende de RR) | ✅ Funcional |
| Runtime | RHS Cross-check Historical | ❌ No data | ✅ Funcional |
| Runtime | Drift Graph | ❌ No data (depende de RR) | ✅ Funcional |
| Cognitive Runtime | Runtime Health Score | ❌ No data | ✅ Funcional |
| Cognitive Runtime | Architecture Risk Score | ❌ No data | ✅ Funcional |
| Cognitive Runtime | Federation Risk (ref A) | ❌ No data | ✅ Funcional |
| Cognitive Runtime | SLO Violations Timeline (ref A) | ❌ No data | ✅ Funcional |
| Cognitive Runtime | Evidence & Replay Risk (ref A) | ❌ No data | ✅ Funcional |

**Total paneles que recuperan datos:** 9

---

## Conclusión

**Resultado: PARTIAL**

Las 5 recording rules están desplegadas y la configuración de Prometheus está actualizada, pero Prometheus requiere un reinicio manual en el servidor 192.168.1.40 para cargar los cambios.

### Comando necesario

```bash
docker restart prometheus
```

Ejecutar en el servidor **192.168.1.40** vía consola local.

### Próxima fase recomendada

**AI-LAB-HEALTH-SCORE-DRIFT-RULE-01** — crear regla de alerta Prometheus para drift >20 entre RHS canónico y cross-check.

**Requiere**: que `ai_lab:runtime_health_score` esté operativa (después del restart de Prometheus).
