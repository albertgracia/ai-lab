# CP-48D-POOL-ALERTING-01

**Resultado: PASS**

## Resumen

Se añadieron 6 reglas de alerting Prometheus para el Elastic Compute Pool en un nuevo archivo de reglas. Sin modificar Router, Gateway, ni Grafana.

## Archivo creado

- **Path:** `/home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-elastic-pool-alerts.yml`
- **Grupo:** `ai-lab-elastic-pool`
- **Intervalo:** 60s (heredado del grupo)

## Reglas añadidas (6)

| Alerta | Expr | For | Severidad |
|--------|------|-----|-----------|
| `AI-LABPoolOffline` | `ailab_pool_nodes_online < 1` | 1m | critical |
| `AI-LABPoolDegraded` | `ailab_pool_nodes_degraded > 0` | 2m | warning |
| `AI-LABPoolFailures` | `increase(ailab_pool_failures_total[5m]) > 5` | 0 | warning |
| `AI-LABPoolFallbackStorm` | `increase(ailab_pool_fallbacks_total[5m]) > 10` | 0 | warning |
| `AI-LABNodeLowScore` | `ailab_pool_node_score < 0.5` | 2m | warning |
| `AI-LABPoolMetricsMissing` | `absent(ailab_pool_nodes_total)` | 0 | critical |

## Archivo modificado

- **Path:** `/home/albert/docker/monitorizacion/prometheus/config/prometheus.yml`
- **Cambio:** añadida línea `  - /etc/prometheus/rules/ai-lab-elastic-pool-alerts.yml` en `rule_files:`

## Backup

```bash
# Rules file (no existía previamente, pero se creó copia por consistencia)
cp /home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-elastic-pool-alerts.yml \
   /home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-elastic-pool-alerts.yml.cp48dbak.20260702_1830

# Prometheus config (backup existía de CP-48B, se usó el mismo)
# cp prometheus.yml.cp48bbak.20260702_1800
```

## Validaciones

### promtool check config (pre-reload)
| Check | Resultado |
|-------|-----------|
| 3 rule files found | ✅ |
| prometheus.yml syntax | ✅ SUCCESS |
| ai-lab-route-family-alerts.yml | ✅ 19 rules |
| ai-lab-cognitive-alerts.yml | ✅ 28 rules |
| **ai-lab-elastic-pool-alerts.yml** | **✅ 6 rules** |

### Prometheus reload
| Paso | Resultado |
|------|-----------|
| `docker kill -s HUP prometheus` | ✅ HUP_OK |
| Log: "Completed loading of configuration file" | ✅ `rules=5.923461ms` |
| Sin errores en logs | ✅ (solo WARN preexistente de gpu-metrics) |

### Post-reload validations

| Check | Resultado |
|-------|-----------|
| 1. Prometheus UP | ✅ API reachable |
| 2. Targets UP | ✅ 19/19, ai-lab-elastic-pool UP |
| 3. 6 reglas cargadas | ✅ ai-lab-elastic-pool group, 6 rules |
| 4. Ninguna en estado firing | ✅ All 6 inactive |
| - AI-LABPoolOffline | ✅ inactive |
| - AI-LABPoolDegraded | ✅ inactive |
| - AI-LABPoolFailures | ✅ inactive |
| - AI-LABPoolFallbackStorm | ✅ inactive |
| - AI-LABNodeLowScore | ✅ inactive |
| - AI-LABPoolMetricsMissing | ✅ inactive |
| 5. Grafana UP | ✅ 200 |
| 6. Dashboard con datos | ✅ `ailab_pool_nodes_online = 3` |
| 7. Logs sin errores post-reload | ✅ |

## Evidencias completas

### promtool output
```
Checking /etc/prometheus/prometheus.yml
  SUCCESS: 3 rule files found
 SUCCESS: /etc/prometheus/prometheus.yml is valid prometheus config file syntax
Checking /etc/prometheus/rules/ai-lab-route-family-alerts.yml
  SUCCESS: 19 rules found
Checking /etc/prometheus/rules/ai-lab-cognitive-alerts.yml
  SUCCESS: 28 rules found
Checking /etc/prometheus/rules/ai-lab-elastic-pool-alerts.yml
  SUCCESS: 6 rules found
```

### Prometheus log post-reload
```
Completed loading of configuration file ... rules=5.923461ms ...
```

### Rules API (post-evaluation)
```
ai-lab-elastic-pool group: 6 rules, all state=inactive
```

### Target status
19 active targets, all UP, ai-lab-elastic-pool included.

## Riesgos residuales

1. **Alertas no probadas con firing real**: todas las métricas del pool están en estado nominal (3/3 online, 0 fallos, scores > 1). No se forzaron condiciones de alerta.
2. **AlertManager no configurado para estas alertas**: las reglas existen en Prometheus pero no hay ruteo a AlertManager configurado (no se modificó). Las alertas son visibles en la API `/api/v1/alerts` y en la UI de Prometheus, pero no se envían a ningún canal.
3. **ai-lab-gpu-metrics WARN preexistente**: los warnings de timestamp duplicado en gpu-metrics (RX9070 y RX7900XT) son previos y no están relacionados.
4. **Sin notificaciones**: las alertas solo existen en Prometheus. No hay Slack, PagerDuty ni email configurado para este proyecto.

## Rollback

```bash
# Opción 1: Eliminar el archivo de reglas
rm /home/albert/docker/monitorizacion/prometheus/config/rules/ai-lab-elastic-pool-alerts.yml

# Opción 2: Restaurar prometheus.yml sin la línea añadida
# (editar manualmente o restaurar backup)
cp /home/albert/docker/monitorizacion/prometheus/config/prometheus.yml.cp48bbak.20260702_1800 \
   /home/albert/docker/monitorizacion/prometheus/config/prometheus.yml

# Reload
docker kill -s HUP prometheus
```

## Próxima fase recomendada

**CP-49 — Pool Admin API**
- Endpoint `POST /admin/nodes` para agregar/quitar nodos sin deploy
- Endpoint `GET /admin/pool/history` para historial de decisiones
- Gestión de pool state vía API
