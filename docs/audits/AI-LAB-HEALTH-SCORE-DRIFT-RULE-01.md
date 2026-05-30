# AI-LAB-HEALTH-SCORE-DRIFT-RULE-01

## Resultado: PASS

---

## Resumen ejecutivo

Se implementó una alerta Prometheus para detectar drift superior a 20 puntos porcentuales
entre el Runtime Health Score canónico y el score de cross-check usado por los dashboards
AI-LAB.

---

## FASE 0 — READ ONLY: Identificación de métricas

### Score canónico

| Atributo | Valor |
|----------|-------|
| Métrica | `ailab_cognitive_health_score{job="ai-lab-gateway"}` |
| Fuente | Gateway `/metrics` — cognitive_health_layer.py |
| Rango | 0-100 (HELP: "Cognitive health score (0-100, metadata-only)") |
| Valor actual | 0.0 (cognitive layer frío, sin datos Qdrant en ventana 60min) |

### Score cross-check

| Atributo | Valor |
|----------|-------|
| Métrica | `ai_lab:runtime_health_score` (recording rule) |
| Fuente | Recording rule en `ai-lab-cognitive-alerts.yml` |
| Rango | 0-1 (raw) → 0-100 en dashboards (`* 100`) |
| Valor actual | 1.0000 (raw) → 100 (en dashboard) |

### Expresiones de drift en dashboards existentes

| Dashboard | Panel | Expresión |
|-----------|-------|-----------|
| AI-LAB Overview | Drift Indicator | `abs(ailab_cognitive_health_score - (ai_lab:runtime_health_score * 100))` |
| AI-LAB Runtime | Drift Graph | `abs(ailab_cognitive_health_score - (ai_lab:runtime_health_score * 100))` |

Ambos scores normalizados a rango 0-100 → no requiere normalización adicional.

---

## FASE 1 — Diseño

### Expresión PromQL

```promql
abs(
  ailab_cognitive_health_score{job="ai-lab-gateway"}
  - (ai_lab:runtime_health_score * 100)
) > 20
```

### Criterio
- **Umbral**: drift >20 puntos porcentuales
- **Duración**: 10 minutos (`for: 10m`) para evitar flapping
- **Severidad**: warning
- **Labels**: `service=ai-lab`, `component=runtime-health`, `type=drift`

---

## FASE 2 — Implementación

### Alerta añadida

```yaml
- alert: AI-LABRuntimeHealthScoreDrift
  expr: |
    abs(
      ailab_cognitive_health_score{job="ai-lab-gateway"}
      - (ai_lab:runtime_health_score * 100)
    ) > 20
  for: 10m
  labels:
    severity: warning
    service: ai-lab
    component: runtime-health
    type: drift
  annotations:
    summary: "Runtime Health Score drift >20% ({{ $value | humanize }} puntos)"
    description: |
      Drift de {{ $value | humanize }} puntos entre cognitive health score
      (ailab_cognitive_health_score) y runtime health score cross-check
      (ai_lab:runtime_health_score*100).
      Umbral superado: >20 puntos durante 10 minutos.
      Causas posibles: cognitive layer frío, Qdrant sin datos,
      desincronización entre capas de salud.
    runbook: "https://github.com/albertgracia/ai-lab/wiki/Runbook-AI-LABRuntimeHealthScoreDrift"
```

### Archivo modificado
`monitorizacion/prometheus/rules/ai-lab-cognitive-alerts.yml` — insertada en grupo
`ai_lab_cognitive_alerts` antes de `ai_lab_cognitive_recording_rules`.

---

## FASE 3 — Validación

### promtool check rules

```text
$ promtool check rules ai-lab-cognitive-alerts.yml
  SUCCESS: 28 rules found
```

De 27 a 28 reglas (22 alerting originales + 1 drift + 5 recording).

### promtool check config

```text
$ promtool check config prometheus.yml
  FAILED: "/etc/prometheus/rules/ai-lab-route-family-alerts.yml" does not point to an existing file
```

FAIL esperado — los paths de rules files son contenedor-internos y no existen
en el host AI-LAB. El YAML es sintácticamente válido.

### Deploy SMB

| Archivo | Destino | Estado |
|---------|---------|--------|
| `ai-lab-cognitive-alerts.yml` | `//192.168.1.40/monitorizacion/prometheus/config/rules/` | ✅ |

### Reload Prometheus

```text
POST /-/reload → HTTP 403 (Lifecycle API deshabilitada)
POST /-/reload → is not enabled.
```

`--web.enable-lifecycle` no está activo en el contenedor en ejecución.
Requiere recrear el container con `docker-compose up -d`.

**Solución**: `docker restart prometheus` por parte del usuario.

---

## FASE 4 — Verificación

### Prometheus — UP

```text
/-/ready → Prometheus Server is Ready.
```

### Reglas — 47 totales (23 + 5 + 19)

| Grupo | Reglas | Estado |
|-------|--------|--------|
| `ai_lab_cognitive_alerts` | 23 alerting | ✅ Todas health=ok |
| `ai_lab_cognitive_recording_rules` | 5 recording | ✅ Todas health=ok |
| `ai-lab-route-family-alerts` | 19 alerting | ✅ Todas health=ok |

### Alerta AI-LABRuntimeHealthScoreDrift

| Atributo | Valor |
|----------|-------|
| state | **pending** (for: 10m en progreso) |
| health | **ok** |
| lastError | **none** |
| duration | 600s (10m) |
| Drift actual | **100.00 puntos** (umbral >20) |

La alerta pasará a `firing` tras 10 minutos continuos de drift >20 puntos.

### Recording Rules

| Regla | Valor | Health |
|-------|-------|--------|
| `ai_lab:runtime_health_score` | **1.0000** | ok |
| `ai_lab:architecture_risk_score` | **0.7000** | ok |
| `ai_lab:federation_guard_events_rate5m` | **0.0000** | ok |
| `ai_lab:evidence_replay_rate5m` | **0.0000** | ok |
| `ai_lab:slo_violations_rate5m` | **0.0074** | ok |

### Targets

```
UP: 12  EXPECTED_OFFLINE: 5  DOWN (real): 0
```

Gateway `up=1` ✅. Todos los targets core de AI-LAB UP.
5 targets EXPECTED_OFFLINE (servidores apagados manualmente) correctamente clasificados.

### Prometheus logs

Sin acceso a `docker logs` en `192.168.1.40`. Servicio responde correctamente
(`/-/ready`, consultas API, evaluación de reglas OK).

---

## Conclusión

**Resultado: PASS**

La alerta AI-LABRuntimeHealthScoreDrift está cargada y evaluándose correctamente.
Entrará en estado `firing` tras 10 minutos de drift continuo >20 puntos.

### Estado actual del drift

| Score | Valor | Escala |
|-------|-------|--------|
| `ailab_cognitive_health_score` | 0.0 | 0-100 |
| `ai_lab:runtime_health_score * 100` | 100.0 | 0-100 |
| **Drift** | **100.0 puntos** | >20 → ALERTA |

El drift actual es del 100% porque el cognitive layer reporta 0 (sin datos Qdrant
en ventana 60min) mientras que el runtime SLO reporta salud perfecta.
Es un comportamiento esperado en estado frío/sin tráfico.

### Próximos pasos recomendados

1. **AI-LAB-GRAFANA-PROVISIONING-VALIDATION-01** — verificación visual de los
   5 dashboards con recording rules operativas (9 paneles recuperados).
2. **AI-LAB-ARCHITECTURE-RECOVERY-01** — solo si el drift actual se considera
   falso positivo y se requiere alinear cognitive layer con runtime.

### Commits

- `12016a0b` — fix(observability): repair 3 recording rules PromQL
- (pendiente) feat(observability): add AI-LABRuntimeHealthScoreDrift alert
