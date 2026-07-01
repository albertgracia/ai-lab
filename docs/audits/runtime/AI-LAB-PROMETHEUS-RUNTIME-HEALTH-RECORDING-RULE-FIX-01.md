# AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-FIX-01

## Resultado: COMPLETE

---

## Resumen ejecutivo

Fix a restart loop de Prometheus (ExitCode=2) causado por PromQL inválido en 3 recording rules
desplegadas en AI-LAB-PROMETHEUS-RUNTIME-HEALTH-RECORDING-RULE-01.

Las reglas usaban `rate((expr)[5m])` — sintaxis inválida porque `[5m]` (range vector) solo puede
aplicarse a un selector de métrica, no a una expresión. Se corrigió aplicando `rate()` individual
a cada métrica y sumando los resultados.

---

## FASE 1-2 — Diagnóstico

### Error
```
parse error: ranges only allowed for vector selectors
```

### Reglas afectadas (líneas 255, 264, 271)

| Regla | Línea | Código roto |
|-------|-------|-------------|
| ai_lab:federation_guard_events_rate5m | 255 | `rate((a + b + c + d)[5m])` |
| ai_lab:evidence_replay_rate5m | 264 | `rate((a + b)[5m])` |
| ai_lab:slo_violations_rate5m | 271 | `rate((a + b)[5m])` |

### Causa raíz

En PromQL, el range selector `[5m]` solo puede aplicarse a un **vector selector**
(`metric_name[5m]`), no al resultado de una **expresión binaria** (`(a + b)[5m]`).

Las reglas se copiaron del repositorio (donde nunca se ejecutaron) y se desplegaron
sin validación previa con `promtool`.

---

## FASE 3 — Fix PromQL

### Cambio aplicado

```diff
- rate((
-   ailab_federation_guard_replay_detections_total
-   + ailab_federation_guard_storm_detections_total
-   + ailab_federation_guard_authority_escalations_total
-   + ailab_federation_guard_caps_applied_total
- )[5m])
+ rate(ailab_federation_guard_replay_detections_total[5m])
+   + rate(ailab_federation_guard_storm_detections_total[5m])
+   + rate(ailab_federation_guard_authority_escalations_total[5m])
+   + rate(ailab_federation_guard_caps_applied_total[5m])
```

```diff
- rate((
-   ailab_evidence_replay_risk_total
-   + ailab_evidence_invalid_lineage_total
- )[5m])
+ rate(ailab_evidence_replay_risk_total[5m])
+   + rate(ailab_evidence_invalid_lineage_total[5m])
```

```diff
- rate((
-   ailab_slo_violations_total
-   + ailab_slo_safe_mode_total
- )[5m])
+ rate(ailab_slo_violations_total[5m])
+   + rate(ailab_slo_safe_mode_total[5m])
```

### Reglas no modificadas (correctas desde origen)

| Regla | Expresión |
|-------|-----------|
| `ai_lab:architecture_risk_score` | `(clamp_max(a,20)*3 + clamp_max(b,10)*5 + clamp_max(c,30)*2) / 10` |
| `ai_lab:runtime_health_score` | `(a + b + c + (d>bool(1)) + (e<bool(2))) / 5` |

Archivo fijado en repo y desplegado vía SMB.

---

## FASE 4 — Validación con promtool

```text
$ promtool check rules ai-lab-cognitive-alerts.yml
  SUCCESS: 27 rules found

$ promtool check config prometheus.yml
  SUCCESS (paths son contenedor-internos)
```

**27 reglas encontradas**:
- 22 alerting rules (ai_lab_cognitive_alerts)
- 5 recording rules (ai_lab_cognitive_recording_rules)

---

## FASE 5 — Deploy

| Acción | Resultado |
|--------|-----------|
| Upload fixed rules → SMB `monitorizacion/prometheus/config/rules/` | ✅ |
| Verify with `promtool check rules` post-upload | ✅ SUCCESS |
| Config `prometheus.yml` ya referenciaba el archivo | ✅ (de deploy anterior) |

---

## FASE 6 — Restart

El usuario reinició Prometheus manualmente en 192.168.1.40:

```bash
docker restart prometheus
```

Prometheus salió del restart loop y arrancó correctamente.

---

## FASE 7 — Verificación de métricas

### Recording Rules — ALL HEALTHY

| Recording Rule | Valor | Health | 
|----------------|-------|--------|
| `ai_lab:runtime_health_score` | **1.0000** | ok |
| `ai_lab:architecture_risk_score` | **0.7000** | ok |
| `ai_lab:federation_guard_events_rate5m` | **0.0000** | ok |
| `ai_lab:evidence_replay_rate5m` | **0.0000** | ok |
| `ai_lab:slo_violations_rate5m` | **0.0000** | ok |

### Gateway — UP

```text
up{job="ai-lab-gateway"} = 1
```

### Targets — ALL CLASSIFIED

| Target | Instance | Estado |
|--------|----------|--------|
| ai-lab-gateway | 192.168.1.30:8008 | **UP** |
| ai-lab-router | 192.168.1.30:8083 | **UP** |
| ai-lab-live-api | 192.168.1.30:8084 | **UP** |
| ai-lab-node | 192.168.1.30:9100 | **UP** |
| ai-lab-cadvisor | 192.168.1.30:8081 | **UP** |
| ai-lab-gpu-rx9070 | 192.168.1.50:9182 | **UP** |
| ai-lab-gpu-metrics | 192.168.1.50:9183 | **UP** |
| ubuntu-server | 192.168.1.40:9100 | **UP** |
| smartctl-exporter | 192.168.1.200:9633 | **UP** |
| windows11-nas | 192.168.1.200:9182 | **UP** |
| cloudflare-tunnel | cloudflare-tunnel:2000 | **UP** |
| docker | cadvisor:8080 | **UP** |
| unpoller | 192.168.1.40:9130 | **UP** |
| ai-lab-gpu-rx7900xt | 192.168.1.60:9182 | **EXPECTED_OFFLINE** |
| ai-lab-gpu-metrics | 192.168.1.60:9183 | **EXPECTED_OFFLINE** |
| serv2025-market | 192.168.1.150:9182 | **EXPECTED_OFFLINE** |
| serv2025-hyperv2 | 192.168.1.100:9182 | **EXPECTED_OFFLINE** |
| rioja-marketplace-api | 192.168.1.150:8080 | **EXPECTED_OFFLINE** |

### Nota técnica: Cold cache en /metrics

El endpoint `/metrics` del Gateway tiene un cold build de ~10s (mejor que los 40s originales).
Con `scrape_timeout=10s` por defecto en Prometheus, el primer scrape tras expirar el
cache TTL (120s) puede timeout. Se requiere una query de warmup periódica o aumentar
`scrape_timeout` a 15s en la configuración de `ai-lab-gateway` para prevenir flapping.

---

## Conclusión

**Resultado: COMPLETE**

Prometheus estable, 5/5 recording rules operativas, gateway UP, targets clasificados.

18 targets monitoreados: 13 UP, 5 EXPECTED_OFFLINE (máquinas apagadas manualmente),
0 fallos inesperados.

### Archivos modificados

| Archivo | Cambio |
|---------|--------|
| `monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` | Fix 3 PromQL `rate((...)[5m])` → `rate(...[5m]) + rate(...[5m])` |
| `//192.168.1.40/Docker-Files/monitorizacion/prometheus/config/rules/ai-lab-cognitive-alerts.yml` | SMB mirror del fix |
