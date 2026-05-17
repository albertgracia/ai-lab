---
title: "Runbook — FASE 17 Observabilidad y Gobernanza"
summary: "Procedimientos operativos para el panel de gobernanza Prometheus/Grafana: verificacion de metricas, solucion de scrape, diagnostico de paneles sin datos."
---

# Runbook — FASE 17 Observabilidad y Gobernanza

## Verificacion rapida

```bash
# 1. Metricas del router (4 contadores)
curl -s http://192.168.1.30:8083/metrics | grep -E 'ailab_router_chat_requests_total|ailab_router_hard_facts_hits_total|ailab_governance_blocked'

# 2. Metricas del gateway
curl -s http://192.168.1.30:8008/metrics | grep -E 'ailab_governance_blocked'

# 3. Prometheus targets
curl -s http://192.168.1.40:9090/api/v1/targets | python3 -c "
import sys,json
data = json.load(sys.stdin)
for t in data['data']['activeTargets']:
    if 'router' in t['labels'].get('job','') or 'gateway' in t['labels'].get('job',''):
        print(f\"{t['health']:4s} {t['scrapeUrl']:55s} job={t['labels'].get('job','')}\")
"

# 4. Query de bloqueos en Prometheus
curl -s 'http://192.168.1.40:9090/api/v1/query?query=ailab_governance_blocked_actions_total'

# 5. Query de ratio Hard Facts
curl -s 'http://192.168.1.40:9090/api/v1/query?query=(sum(rate(ailab_router_hard_facts_hits_total%5B1m%5D))%20/%20sum(rate(ailab_router_chat_requests_total%5B1m%5D))%20*%20100)%20or%20vector(0)'
```

## Problemas comunes

### Panel Ratio muestra "No data"

**Causa:** La metrica `ailab_router_chat_requests_total` es demasiado nueva y `rate([1m])` no encuentra scrapes suficientes en la ventana.

**Solucion:** La query ya incluye `or vector(0)` como respaldo. Si persiste "No data", verificar que el router esta scrapeando: `curl -s http://192.168.1.40:9090/api/v1/targets | grep ai-lab-router`.

### Panel Ratio muestra ∞

**Causa:** Division por cero. `ailab_router_chat_requests_total` no tiene datos porque nadie ha llamado al router desde el ultimo reinicio.

**Solucion:** Enviar una peticion al router (`curl http://192.168.1.30:8083/v1/chat/completions ...`) para que el contador de peticiones se active.

### Panel Alertas muestra "No data"

**Causa:** El contador sin labels `ailab_governance_blocked_actions_total` no se esta exportando. Probablemente el router o gateway no se reinicio tras el despliegue.

**Solucion:**
```bash
sudo systemctl restart ailab-router ailab-gateway
curl -s http://192.168.1.30:8083/metrics | grep governance_blocked_actions_total
```

### Prometheus no scrapea el router

**Causa:** Falta el job `ai-lab-router` en `prometheus.yml`.

**Solucion:**
1. Editar `/home/albert/docker/monitorizacion/prometheus/config/prometheus.yml` en `.40`
2. Anadir:
   ```yaml
   - job_name: ai-lab-router
     scrape_interval: 15s
     metrics_path: /metrics
     static_configs:
     - labels:
         cluster: ai-lab
         env: homelab
         role: router
       targets:
       - 192.168.1.30:8083
   ```
3. Recargar: `docker exec prometheus kill -HUP 1`

### Los contadores no suben

**Causa:** No se han recibido comandos peligrosos desde el reinicio.

**Solucion:** Enviar un prompt al chat del router pidiendo comandos peligrosos. Si el modelo de LM Studio responde con `<tool_call>` que contenga `rm -rf`, `sudo`, `reboot`, etc., los contadores se incrementaran y el panel de Grafana lo reflejara en ~15s.
