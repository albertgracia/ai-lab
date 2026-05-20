# CHANGELOG — AI-LAB
## Registro de operaciones y cambios

---

### 18/05/2026 — Corrección de Socratic Gate para informes

#### Estado final
- Las peticiones de resumen/informe/estado dejan de pasar por `question`.
- La guía de OpenCode y la capa `.agent` ahora distinguen entre aclaración real y respuestas directas.
- Se evita el `SchemaError(Expected array, got "[...]")` al intentar serializar `questions` como string.

#### Problemas resueltos
- Falsos positivos del Socratic Gate en solicitudes abiertas de informe.
- Uso incorrecto de `question` como herramienta genérica para resúmenes.

#### Documentación actualizada
- `.agent/OPENCODE_PROMPT.md`
- `.agent/BOOTSTRAP.md`
- `.agent/rules/GEMINI.md`
- `apps/ialab-docs/src/content/docs/parche-opencode-router-gateway.md`

---

### 18/05/2026 — Parche OpenCode + Router/Gateway Streaming

#### Estado final
- OpenCode quedó documentado para responder informes y resúmenes de forma directa, sin usar `question` cuando la respuesta es abierta.
- Router y gateway quedaron alineados con SSE compatible y retry ante `Model unloaded`.
- Se añadió trazabilidad en Astro con un doc específico del parche.

#### Problemas resueltos
- `SchemaError(Expected array, got "[...]")` al pasar `questions` como string.
- Incompatibilidad de streaming entre cliente y backend cuando LM Studio devolvía respuestas no triviales.
- Falsos cuelgues por mezcla de JSON/SSE en el flujo de conversación.

#### Documentación actualizada
- `apps/ialab-docs/src/content/docs/parche-opencode-router-gateway.md`
- `apps/ialab-docs/src/content/docs/fix-model-unloaded-lmstudio.md`
- `apps/ialab-docs/src/content/docs/retrospectiva-fase18-incidente.md`
- `apps/ialab-docs/src/content/docs/openwebui-conexion-router.md`

---

### 16/05/2026 — Restauración telemetría GPU

#### Estado final
- `192.168.1.50:9182` volvió a emitir `windows_gpu_*` tras reactivar el collector `gpu`.
- `192.168.1.50:9183` y `192.168.1.60:9183` volvieron a servir métricas GPU válidas con labels citados.
- `GPU AI Metrics`, `AI-LAB GPUs` y `metricas.labrazahome.com/gpus` quedaron verificados con RX9070 + RX7900XT.

#### Problemas resueltos
- Regresión del reboot: `windows_exporter` quedó sin `gpu` en `.50`.
- Regresión del reboot: `gpu_metrics.ps1` en `.60` emitía labels sin comillas y Prometheus lo rechazaba.
- `GPUExporter` pasó a ejecutarse con `powershell.exe -File gpu_metrics.ps1` directo.

#### Documentación actualizada
- `docs/opencode/09-observabilidad.md`
- `docs/opencode/ai-lab-estado.md`
- `docs/opencode/ai-lab-informe-tecnico.md`
- `apps/ialab-docs/src/content/docs/telemetria-gpu-restauracion.md`

---

### 16/05/2026 — Consolidación de observabilidad

#### Estado final
- Grafana consolidado en `192.168.1.40:3000`.
- Grafana antiguo retirado.
- Prometheus y Loki operativos en `192.168.1.40:9090` y `192.168.1.40:3100`.
- Promtail en `192.168.1.30` recibe `unifi-ids` por `TCP :1514`.

#### Problemas resueltos
- `Labrazahome — Logs` corregido con el datasource Loki `fflfh9qp8mxogc`.
- `Labrazahome — Time-Series Analysis` corregido con el datasource Loki `fflfh9qp8mxogc` y la query `job="unifi-ids"`.
- `Windows Server - NAS N5` restauró el panel `Temperatura SMART discos` usando `smartctl-exporter` en `192.168.1.200:9633`.
- Dashboards `AI-LAB Overview`, `AI-LAB Runtime`, `AI-LAB GPUs` y `AI-LAB Infrastructure` corregidos.
- Se eliminaron las referencias al Grafana antiguo en la documentación operativa.

#### Documentación actualizada
- `docs/opencode/09-observabilidad.md`
- `docs/opencode/03-operaciones.md`
- `docs/opencode/CHANGELOG.md`

---

### 13/05/2026 — Stack de Observabilidad + Migración Dashboards

#### Nuevos contenedores Docker
| Servicio | Puerto | Versión |
|----------|--------|---------|
| Grafana | 3000 | 13.0.1 |
| Node Exporter | 9100 | v1.9.1 |
| cAdvisor | 8081 | v0.52.1 |

#### Targets Prometheus (.40)
- `ai-lab-node` (.30:9100) — ✅ UP
- `ai-lab-cadvisor` (.30:8081) — ✅ UP

#### Dashboards en Grafana (.40:3000 — admin/19682507)
- Node Exporter Full (ID 1860) — provisionado
- Cadvisor exporter (ID 14282) — provisionado
- Labrazahome — Logs (al6k9h6) — migrado desde Cloud
- Labrazahome — Time-Series Analysis (alpt7gt) — migrado desde Cloud
- UniFi Access Points WiFi (al79ptk) — migrado desde Cloud
- UniFi Cloud Gateway Fiber (alw8vm9) — migrado desde Cloud
- UniFi Switch USW Flex 2.5G 8 PoE (al2m9l8) — migrado desde Cloud
- Windows Server — NAS N5 (aldh6t8) — migrado desde Cloud

#### Documentación generada
- `docs/opencode/01-arquitectura.md`
- `docs/opencode/02-api-modulos.md`
- `docs/opencode/03-operaciones.md`
- `docs/opencode/04-seguridad.md`
- `docs/opencode/05-desarrollo.md`
- `docs/opencode/06-hardware-infra.md`
- `docs/opencode/07-ecosistema-agent.md`
- `docs/opencode/08-despliegue.md`
- `docs/opencode/09-observabilidad.md`
- `docs/opencode/ai-lab-informe-tecnico.md`
- `docs/opencode/ai-lab-venta-pymes.md`
- `docs/opencode/ai-lab-estado.md`
- `docs/opencode/ai-lab-informe-detallado.md`
- `docs/opencode/CHANGELOG.md` ← este archivo

#### Archivos de configuración
- `stacks/observability/docker-compose.yml`
- `stacks/observability/grafana/provisioning/datasources/datasources.yml`
- `stacks/observability/grafana/provisioning/dashboards/dashboards.yml`
- `stacks/observability/grafana/provisioning/dashboards/migrated/` (6 dashboards)

#### Modificaciones
- `stacks/ai-core/docker-compose.yml` — añadido `OLLAMA_METRICS=1`
- `prometheus.yml` en VM .40 — añadidos targets ai-lab-node, ai-lab-cadvisor; eliminado ai-lab-ollama (no soporta métricas)
- `stacks/observability/docker-compose.yml` — contraseña Grafana actualizada a `19682507`

### 13/05/2026 — Corrección unpoller + Escaneo de red

#### Corrección unpoller en VM .40
- **Antes:** `UP_UNIFI_CONTROLLER_0_URL=https://unifi.ui.com:443` (cloud, REMOTE=true, API key)
  → Error: "unable to get server version: invalid character '<'" (HTML en vez de JSON)
- **Después:** `UP_UNIFI_CONTROLLER_0_URL=https://192.168.1.1:443` (local, REMOTE=false, user/pass)
  → Éxito: 3.167 métricas UniFi exportadas, 0 errores
- **Archivo modificado:** `/home/albert/docker/monitorizacion/unpoller/.env` en VM .40
- **Usuario creado en UniFi:** `opencode-agent` (View Only)
- **Credenciales:** opencode-agent / GemaLabraza2026??

#### Escaneo de infraestructura de red
- **API UniFi Gateway:** 4 dispositivos de red detectados (Gateway, Switch, 2 APs)
- **Clientes activos:** 19 (LAN + IoT + Guest VLANs)
- **Escaneo por ping:** 13 hosts en 192.168.1.0/24
- **Detalles guardados** en `09-observabilidad.md` sección 6.6

#### Documentación actualizada
- `09-observabilidad.md` — añadida sección unpoller + inventario de red completo
- `CHANGELOG.md` — registro de esta operación

### 13/05/2026 — Promtail + Syslog UniFi IDS

#### Nuevo contenedor
| Servicio | Puerto | Imagen |
|----------|--------|--------|
| Promtail | 1514/tcp, 9080 | grafana/promtail:3.4.2 |

#### Fuentes de logs añadidas a Loki (.40:3100)
| Job | Fuente | Estado |
|-----|--------|--------|
| `docker` | Contenedores Ubuntu (.30) vía Docker socket | ✅ |
| `journald` | Sistema Ubuntu (.30) vía /var/log/journal | ✅ |
| `unifi-ids` | UniFi Gateway → syslog TCP .30:1514 → Promtail → Loki | ✅ |

#### Archivos de configuración creados
- `stacks/promtail/docker-compose.yml` — contenedor Promtail
- `stacks/promtail/promtail.yml` — configuración (Docker SD + journald + syslog)

#### Correcciones aplicadas
- Dashboard Windows NAS-N5: reemplazadas 25 referencias `localhost:9182` → `192.168.1.200:9182`
- promtail.yml ajustes: syslog listener en TCP/RFC5424 (formato que espera Promtail 3.4.2)

### 13/05/2026 — Reparación Rioja Marketplace

#### Problemas resueltos
- **Frontend reconstruido** — Next.js 15.5.15 build completado con 25 rutas
- **Rutas 404 → 200** — admin, checkout, client-portal, b2b, etc. ahora funcionan
- **LM Studio** — URLs actualizadas de localhost → NAS-N5 (192.168.1.250:1234)
- **Fotos de productos** — 20 fotos copiadas desde backup original
- **Nginx config** — actualizado para proxy_pass a puerto correcto
- **Servicios** — nginx, Next.js y Go API todos operativos

#### Rutas verificadas
| Ruta | Estado |
|------|--------|
| `/`, `/login`, `/register`, `/b2b` | ✅ 200 |
| `/vinos`, `/aceites`, `/mieles` | ✅ 200 |
| `/sommelier`, `/tracking` | ✅ 200 |
| `/admin/*` (clientes, config, facturacion, inventario, logistica) | ✅ 307 (auth) |
| `/checkout/success`, `/client-portal` | ✅ 200 |
| `/mapa-suelos`, `/municipios`, `/terminos-b2b` | ✅ 200 |

#### Pendiente para próxima sesión
- **Resetear contraseñas de administración** del marketplace (las anteriores no funcionan)
- Crear servicios Windows (nginx, Next.js, Go API) con NSSM
- Proteger Stripe keys en variables de entorno del sistema
- Configurar backup automático de PostgreSQL
- Monitoring con Prometheus + Grafana

### 13/05/2026 — Recuperación proyectos antiguos

#### Proyectos restaurados desde `\\192.168.1.200\e\Webs` a AI-LAB

| Proyecto | Tipo | Servicio | Traefik host | 
|----------|------|----------|-------------|
| AGITHome | Web estática (HTML+CSS+JS) | nginx:alpine | `agithome.lab` |
| AGITServices | Web estática (HTML+CSS+JS) | nginx:alpine | `agitservices.lab` |
| AlbertSkills | Web estática (HTML+CSS+JS) | nginx:alpine | `albertskills.lab` |
| AlbertSkillsAMDMulti | React + Vite (estático) | nginx:alpine | `skills.lab` |
| Calavera LAB | Node + Express + Stripe | Node 24 | `calavera.lab` |
| Musquera RAW LAB | Node + Express + PostgreSQL | Node 18 + Postgres 15 + nginx | `musquera.lab` |

#### Infraestructura creada
- `/opt/ai-lab/stacks/websites/docker-compose.yml` — 4 sitios estáticos
- `/opt/ai-lab/stacks/websites/docker-compose.backend.yml` — 2 proyectos backend
- `musquera-db-data` — volumen PostgreSQL persistente
- `musquera-uploads` — volumen para uploads

#### Documentación
- `docs/opencode/10-proyectos-restaurados.md` — puertos, dominios, gestión, Cloudflare
