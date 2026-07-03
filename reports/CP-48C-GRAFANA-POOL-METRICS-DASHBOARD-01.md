# CP-48C-GRAFANA-POOL-METRICS-DASHBOARD-01

**Resultado: PASS**

## Resumen

Crear dashboard Grafana para visualizar métricas del Elastic Compute Pool usando provisioning JSON.

## Método elegido

Grafana provisioning por JSON en filesystem: se colocó el archivo en el directorio de provisioning `/home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/`. Grafana lo carga automáticamente (sin restart).

## Dashboard creado

- **Nombre:** AI-LAB Elastic Compute Pool
- **UID:** `ai-lab-elastic-pool`
- **URL:** `/d/ai-lab-elastic-pool/ai-lab-elastic-compute-pool`
- **Carpeta:** AI-LAB
- **Datasource:** Prometheus (`PBFA97CFB590B2093`)
- **Refresh:** 30s
- **Time range:** now-6h

## Backup

```bash
# Copia de seguridad del JSON (no existía previamente)
cp /home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/ai-lab-elastic-pool.json \
   /home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/ai-lab-elastic-pool.json.cp48cbak.20260702_1815
```

## Panels incluidos (9)

| # | Panel | Tipo | Query |
|---|-------|------|-------|
| 1 | Pool Nodes Online | stat | `ailab_pool_nodes_online` |
| 2 | Pool Nodes Total | stat | `ailab_pool_nodes_total` |
| 3 | Pool Selections Total | stat | `ailab_pool_selections_total` |
| 4 | Node Score | timeseries | `ailab_pool_node_score` |
| 5 | Node Selected Total | timeseries | `ailab_pool_node_selected_total` |
| 6 | Node Failures Total | timeseries | `ailab_pool_node_failure_total` |
| 7 | Node Fallback Total | timeseries | `ailab_pool_node_fallback_total` |
| 8 | Node Online State | stat | `ailab_pool_node_online` |
| 9 | Node Degraded State | stat | `ailab_pool_node_degraded` |

Columnas: 3 (grid de 12), Filas: 3 (Stat summary → Time series → Node states)

Todos los targets usan `legendFormat: {{node}}` para mostrar nombres de nodo.

## Validaciones

### Dashboard
| Check | Resultado |
|-------|-----------|
| Dashboard existe | ✅ uid=ai-lab-elastic-pool |
| Título correcto | ✅ "AI-LAB Elastic Compute Pool" |
| En carpeta AI-LAB | ✅ folderUid=afm31iddgfcaoa |
| 9 panels | ✅ todos con queries correctas |
| Datasource Prometheus | ✅ PBFA97CFB590B2093 en todos |

### Prometheus queries desde el dashboard
| Query | Datos |
|-------|-------|
| `ailab_pool_nodes_online` | 3 |
| `ailab_pool_nodes_total` | 3 |
| `ailab_pool_selections_total` | 3 |
| `ailab_pool_node_score` | nas-n5=2, rx9070-node=2, rx7900xt-node=2 |
| `ailab_pool_node_selected_total` | rx9070-node=3, resto=0 |
| `ailab_pool_node_failure_total` | todos=0 |
| `ailab_pool_node_fallback_total` | todos=0 |
| `ailab_pool_node_online` | todos=1 |
| `ailab_pool_node_degraded` | todos=0 |

### Infraestructura
| Check | Resultado |
|-------|-----------|
| Grafana UP | ✅ Up about 1h |
| Prometheus UP | ✅ Up |
| ai-lab-elastic-pool target UP | ✅ UP |
| Dashboards existentes no rotos | ✅ (provisioning additivo) |

## Riesgos residuales

1. **Sin autenticación automatizada**: dashboard accesible via Grafana login estándar. No se creó API key.
2. **Stat panels sin rate()**: los contadores `_total` se muestran como instantáneas, no como tasa. Si se quiere rate, añadir `rate(metric[5m])` en panels específicos.
3. **Sin alertas**: dashboard visual solamente. Alertas para pool metrics no están configuradas.
4. **Provisioning no versionado**: el JSON no está bajo git (el directorio de monitorización no tiene repo).
5. **No se probó con fallos/fallbacks**: todas las métricas están a 0 excepto selections.

## Rollback

```bash
# Restaurar backup (o eliminar archivo)
rm /home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/ai-lab-elastic-pool.json
# O restaurar backup si existía
cp /home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/ai-lab-elastic-pool.json.cp48cbak.20260702_1815 \
   /home/albert/docker/monitorizacion/grafana/provisioning/dashboards/AI-LAB/ai-lab-elastic-pool.json
# Grafana reloads automáticamente
```

## Próxima fase recomendada

**CP-49 — Pool Admin API**
- Endpoint `POST /admin/nodes` para agregar/quitar nodos sin deploy
- Endpoint `GET /admin/pool/history` para historial de decisiones
- Gestión de pool state vía API
