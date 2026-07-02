# CP-48B-PROMETHEUS-SCRAPE-TARGET-CONFIG-01

**Resultado: PASS**

## Resumen

Añadir scrape target `ai-lab-elastic-pool` en Prometheus para recolectar métricas del Elastic Compute Pool desde AI-LAB Gateway.

## Archivo tocado

`/home/albert/docker/monitorizacion/prometheus/config/prometheus.yml` (en 192.168.1.40)

## Backup creado

```
/home/albert/docker/monitorizacion/prometheus/config/prometheus.yml.cp48bbak.20260702_1800
```

## Cambio aplicado

Nuevo scrape job insertado antes de `rioja-marketplace-api`:

```yaml
- job_name: ai-lab-elastic-pool
  scrape_interval: 15s
  metrics_path: /runtime/pool/prometheus
  static_configs:
  - targets:
    - 192.168.1.30:8008
    labels:
      cluster: ai-lab
      env: homelab
      role: pool
```

## Validación de sintaxis

```bash
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
```
✅ SUCCESS: 2 rule files found, config is valid

## Reload ejecutado

```bash
docker kill -s HUP prometheus
```
✅ Sin downtime, sin reinicio.

## Validaciones (14/14 PASS)

### Targets
| Job | Health | Estado |
|-----|--------|--------|
| `ai-lab-elastic-pool` | up | ✅ **NUEVO** |
| `ai-lab-gateway` | up | ✅ sin cambios |
| `ai-lab-router` | up | ✅ sin cambios |
| `ai-lab-live-api` | up | ✅ sin cambios |
| `ai-lab-gpu-rx9070` | up | ✅ sin cambios |
| `ai-lab-gpu-rx7900xt` | up | ✅ sin cambios |
| `ai-lab-node` | up | ✅ sin cambios |
| +12 otros targets existentes | up | ✅ |

### Queries PromQL
| Query | Resultado |
|-------|-----------|
| `ailab_pool_nodes_total` | 3 |
| `ailab_pool_nodes_online` | 3 |
| `ailab_pool_selections_total` | 3 |
| `ailab_pool_node_score{node="nas-n5"}` | 2 |
| `ailab_pool_node_score{node="rx9070-node"}` | 2 |
| `ailab_pool_node_score{node="rx7900xt-node"}` | 2 |

### Total targets activos: 19 (antes 18)

## Riesgos residuales

1. **Sin `--web.enable-lifecycle`**: el reload requiere `docker kill -s HUP`. Si el contenedor se reinicia, la señal HUP no persiste. Mejora futura: añadir flag.
2. **Config Prometheus no está en git**: el directorio `/home/albert/docker/monitorizacion/` no tiene control de versiones.
3. **Sin dashboard Grafana**: métricas disponibles en Prometheus pero sin visualización todavía.
4. **scrape_interval 15s**: puede ajustarse según necesidades operativas.

## Rollback

```bash
cp /home/albert/docker/monitorizacion/prometheus/config/prometheus.yml.cp48bbak.20260702_1800 \
   /home/albert/docker/monitorizacion/prometheus/config/prometheus.yml
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml  # verificar
docker kill -s HUP prometheus
```

O restaurar desde backup original:
```bash
# Backup ya existe
```

## Próxima fase recomendada

**CP-48C — Pool Metrics Dashboard en Grafana**
- Dashboard Grafana para pool metrics (selections, scores, online/degraded, per-node)
- Datasource: Prometheus (PBFA97CFB590B2093)
- Carpeta: AI-LAB
- TIER: 1 o 2
