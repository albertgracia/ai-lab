# ANYTHINGLLM-ENTERPRISE-04B3-OBSERVABILITY-IDS-IMPORT

**Estado:** ✅ COMPLETADO  
**Fecha:** 2026-07-05  
**Pre-requisito:** 04B2 (Marketplace Import)  
**Siguiente:** 04B4 (subfase a determinar)

---

## Objetivo

Importar documentación canónica de Observabilidad (Prometheus, Grafana, Loki, Alertas) e IDS (UniFi IDS/IPS, SOC) en el workspace dedicado.

## Documentos Importados (2)

| Archivo | Tamaño | Contenido |
|---------|--------|-----------|
| `docs/opencode/09-observabilidad.md` | 24.9KB | Stack completo de observabilidad: Prometheus, Grafana, Loki, Promtail, cAdvisor, Node Exporter, dashboards, alertas, UniFi IDS, infraestructura de red |
| `docs/runtime/runtime-observability-alerts-39b.md` | 3.7KB | Alertas runtime, SLO, circuit breakers, métricas Prometheus |

**Total: 2 documentos, ~29KB, +27 vectores (sistema: 1049)**

## Cobertura por Tema

Los 2 documentos cubren todos los temas solicitados:

| Tema | Cobertura | Documento principal |
|------|-----------|-------------------|
| **Prometheus** | Targets (.30:8008, 8083, 8084, .50:9182, .60:9182), alertas (19 reglas), scrape config, métricas `ailab_*` | 09-observabilidad.md |
| **Grafana** | 15 dashboards (Tier 1/2), datasource UID, provisioning, troubleshooting | 09-observabilidad.md |
| **Loki** | Centralizado en .40:3100, datasource en Grafana, logs Docker/journald/UniFi | 09-observabilidad.md |
| **Alertas** | 19 reglas activas (route regression, tool_fastpath, governance, HARD_FACTS, etc.) | ambos docs |
| **IDS/IPS** | UniFi Cloud Gateway Fiber → syslog TCP :1514 → Promtail → Loki | 09-observabilidad.md |
| **SOC** | Eventos de seguridad del Gateway UniFi, dashboards de logs | 09-observabilidad.md |
| **UniFi** | unpoller (3,682 métricas), Access Points, Cloud Gateway, Switch | 09-observabilidad.md |

**Nota sobre Suricata:** No existe instancia independiente de Suricata en el stack. La funcionalidad IDS/IPS la proporciona el UniFi Cloud Gateway Fiber incorporado, que envía eventos vía syslog. Las consultas sobre "Suricata" retornan documentos de observabilidad genérica con score ~0.865.

## Smoke RAG

| Consulta | Score | Fuente principal |
|----------|-------|-----------------|
| Prometheus AI-LAB targets alerts | 0.8923 | 09-observabilidad.md (1104ch) |
| Grafana dashboards AI-LAB datasource | 0.8932 | 09-observabilidad.md (1104ch) |
| Alertas AI-LAB route family | 0.8697 | runtime-observability-alerts-39b.md (1035ch) |
| IDS UniFi Cloud Gateway syslog | 0.8846 | 09-observabilidad.md (1029ch) |
| Suricata IPS seguridad red | 0.8656 | runtime-observability-alerts-39b.md (1095ch) |
| UniFi Access Points Cloud Gateway | 0.8854 | 09-observabilidad.md (1104ch) |
| Promtail syslog unifi-ids loki | 0.8802 | 09-observabilidad.md (1104ch) |
| Loki centralizado logs AI-LAB | 0.8942 | 09-observabilidad.md (1101ch) |
| cAdvisor Node Exporter infra | 0.8906 | runtime-observability-alerts-39b.md (1095ch) |
| ¿Cómo funciona observabilidad en AI-LAB? | 0.8889 | 09-observabilidad.md (1104ch) |
| What Prometheus targets does AI-LAB have? | 0.8780 | 09-observabilidad.md (1104ch) |

## Cross-check: Sin Contaminación

| Workspace | Query "Prometheus" | Query "UniFi IDS" | Query "Grafana" |
|-----------|-------------------|-------------------|-----------------|
| Hermes Enterprise | ✅ Hermes docs | ✅ Hermes docs | ✅ Hermes docs |
| Reports | ✅ Hermes-Operator | ✅ Hermes docs | ✅ Hermes-Architecture |
| Marketplace | ✅ Integration | ✅ GitNexus | ✅ GitNexus |
| **Observabilidad** | **09-observabilidad.md** | **09-observabilidad.md** | **09-observabilidad.md** |

**Sin fuga.** Las referencias a observabilidad en workspaces ajenos son menciones arquitectónicas (Hermes), no documentos del stack de observabilidad.

## Observaciones

### Chunks de Tamaño Uniforme

A diferencia de importaciones anteriores, ambos documentos producen chunks de 1000-1100 caracteres (sin fragmentos cortos de 100-200ch). Esto se debe a que son documentos Markdown con párrafos largos y tablas, sin JSON/YAML ni sintaxis fragmentada.

### Suricata no existe como servicio independiente

El stack IDS/IPS de AI-LAB usa el UniFi Cloud Gateway Fiber incorporado, no Suricata. Las consultas sobre "Suricata" retornan documentos de observabilidad genérica. Si se desplegara Suricata en el futuro, debería documentarse e importarse separadamente.

## Conclusión

| Aspecto | Resultado |
|---------|-----------|
| Documentos importados | ✅ 2/2 |
| Vectores generados | ✅ +27 (sistema: 1049) |
| Prometheus | ✅ recuperable |
| Grafana | ✅ recuperable |
| Loki | ✅ recuperable |
| Alertas | ✅ recuperable |
| IDS/IPS (UniFi) | ✅ recuperable |
| UniFi (red) | ✅ recuperable |
| Recall general | ✅ 12/12 consultas con resultados relevantes |
| Contaminación cruzada | ✅ Sin fuga |

## Estado de la Ingesta

```
Workspace: hermes-enterprise (canónico)
  46 documentos, 467 vectores

Workspace: reports (evidencia histórica)
  53 documentos, 456 vectores

Workspace: rioja-marketplace
  7 documentos, 99 vectores

Workspace: observabilidad (+IDS)
  2 documentos, 27 vectores

Total sistema: 1049 vectores
Embedder: multilingual-e5-small (Q8_0, LM Studio .50:1234)
```

---

*Fin del reporte 04B3*
