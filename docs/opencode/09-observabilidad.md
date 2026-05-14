# INFORME DE IMPLEMENTACIÓN: Stack de Observabilidad AI-LAB
## Grafana 12.0.2 + Node Exporter + cAdvisor + Prometheus/Loki
### Fecha: 13 de mayo de 2026

---

## 1. RESUMEN DE LA IMPLEMENTACIÓN

| Componente | Estado | Puerto | Versión |
|-----------|--------|--------|---------|
| **Grafana** | ✅ Operativo | 3001 | 12.0.2 |
| **Node Exporter** | ✅ Operativo | 9100 | v1.9.1 |
| **cAdvisor** | ✅ Operativo | 8081 | v0.52.1 |
| **Datasource Prometheus** | ✅ Configurado | → 192.168.1.40:9090 | — |
| **Datasource Loki** | ✅ Configurado | → 192.168.1.40:3100 | — |
| **Dashboard Node Exporter Full** | ✅ Importado | ID 1860 | — |
| **Dashboard cAdvisor** | ✅ Importado | ID 14282 | — |

---

## 2. ARQUITECTURA FINAL

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       NAS-N5 (192.168.1.250) Windows 11 Pro              │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Alloy → remote_write → 192.168.1.40:9090                        │   │
│  │  Alloy → loki.write  → 192.168.1.40:3100                        │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                 VM Prometheus/Loki (192.168.1.40)                        │
│                                                                         │
│  ┌─────────────────────────┐    ┌──────────────────────────┐            │
│  │  Prometheus :9090       │    │  Loki :3100               │            │
│  │                         │    │                          │            │
│  │  Targets:               │    │  Logs desde Alloy        │            │
│  │  - Alloy (windows_exp.) │    │  (System + Application)  │            │
│  │  - Alloy (smartctl)     │    │                          │            │
│  │  - unpoller (UniFi)     │    └──────────────────────────┘            │
│  │  - ai-lab-node (:9100)  │                                           │
│  │  - ai-lab-ollama (:11434)│                                           │
│  │  - ai-lab-cadvisor (:8081)│                                          │
│  └─────────────────────────┘                                           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ▲
                                    │ query
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│                   Ubuntu AI-LAB (192.168.1.30)                           │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      NUEVOS CONTENEDORES                          │   │
│  │                                                                  │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │   │
│  │  │   Grafana      │  │  Node Exporter │  │    cAdvisor      │   │   │
│  │  │   :3001        │  │  :9100         │  │   :8081          │   │   │
│  │  │   v12.0.2      │  │  v1.9.1        │  │   v0.52.1        │   │   │
│  │  │                │  │                │  │                  │   │   │
│  │  │  datasources:  │  │  1334 métricas │  │  918 métricas    │   │   │
│  │  │  → .40:9090 🔗 │  │  CPU/RAM/disco │  │  por contenedor  │   │   │
│  │  │  → .40:3100 🔗 │  │  systemd/proc  │  │  Docker only      │   │   │
│  │  └────────────────┘  └────────────────┘  └──────────────────┘   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    CONTENEDORES EXISTENTES                         │   │
│  │  Traefik :80 | Open WebUI :3000 | Ollama :11434 (con métricas)    │   │
│  │  Qdrant :6333 | Portainer :9000                                   │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. PASO A PASO: IMPLEMENTACIÓN

### 3.1. Crear estructura de directorios

```bash
mkdir -p /opt/ai-lab/stacks/observability/grafana/provisioning/datasources
mkdir -p /opt/ai-lab/stacks/observability/grafana/provisioning/dashboards
mkdir -p /opt/ai-lab/stacks/observability/grafana/data
```

### 3.2. docker-compose.yml

```yaml
services:
  grafana:
    image: grafana/grafana:12.0.2
    container_name: grafana
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      TZ: Europe/Madrid
      GF_SECURITY_ADMIN_PASSWORD: "CAMBIAR"
      GF_USERS_ALLOW_SIGN_UP: "false"
    volumes:
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/data:/var/lib/grafana
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - proxy
    labels:
      env: homelab
      cluster: ai-lab
      role: observability

  node-exporter:
    image: prom/node-exporter:v1.9.1
    container_name: node-exporter
    restart: unless-stopped
    ports:
      - "9100:9100"
    environment:
      TZ: Europe/Madrid
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
      - '--collector.systemd'
      - '--collector.processes'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($|/)'
    networks:
      - proxy
    labels:
      env: homelab
      cluster: ai-lab
      role: system

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.52.1
    container_name: cadvisor
    restart: unless-stopped
    ports:
      - "8081:8080"
    environment:
      TZ: Europe/Madrid
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    devices:
      - /dev/kmsg
    privileged: true
    command:
      - '--docker_only=true'
      - '--housekeeping_interval=30s'
    networks:
      - proxy
    labels:
      env: homelab
      cluster: ai-lab
      role: containers

networks:
  proxy:
    external: true
```

### 3.3. Datasources (provisioning automático)

`grafana/provisioning/datasources/datasources.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://192.168.1.40:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://192.168.1.40:3100
    isDefault: false
    editable: false
```

### 3.4. Dashboards (provisioning automático)

Dashboards descargados e importados automáticamente:
- **Node Exporter Full** (ID 1860) — 468 KB
- **Cadvisor Exporter** (ID 14282) — 19 KB

### 3.5. Ajustar permisos

```bash
chmod 777 /opt/ai-lab/stacks/observability/grafana/data
```
> Nota: El contenedor Grafana corre como UID 472. Para producción, usar `chown 472:472` con sudo.

### 3.6. Desplegar

```bash
cd /opt/ai-lab/stacks/observability
docker compose up -d
```

---

## 4. CONFIGURACIÓN DE PROMETHEUS EN VM .40

Añadir estos 3 jobs al `prometheus.yml` de la máquina 192.168.1.40:

```yaml
  - job_name: 'ai-lab-node'
    scrape_interval: 15s
    static_configs:
      - targets:
        - '192.168.1.30:9100'
      labels:
        env: homelab
        cluster: ai-lab
        role: system

  - job_name: 'ai-lab-cadvisor'
    scrape_interval: 30s
    static_configs:
      - targets:
        - '192.168.1.30:8081'
      labels:
        env: homelab
        cluster: ai-lab
        role: containers
```

Luego recargar Prometheus:
```bash
# Si corre como servicio:
sudo systemctl reload prometheus
# Si corre en contenedor:
docker compose restart prometheus
# O vía API:
curl -X POST http://localhost:9090/-/reload
```

---

## 5. VERIFICACIÓN POST-DESPLIEGUE

### 5.1. Estado actual

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E "grafana|node-exporter|cadvisor"
```

### 5.2. Endpoints locales

```bash
# Node Exporter
curl http://localhost:9100/metrics | head -5

# cAdvisor
curl http://localhost:8081/metrics | head -5

# Grafana
curl http://localhost:3001/api/health
```

### 5.3. Targets en Prometheus

```
Abrir: http://192.168.1.40:9090/targets
Buscar: ai-lab-node, ai-lab-cadvisor → deben aparecer UP
```

### 5.4. Acceso a Grafana

```
URL:  http://192.168.1.30:3001
User: admin
Pass: 19682507 (configurado en docker-compose.yml)
```

### 5.5. Consulta rápida

```bash
curl -s 'http://192.168.1.40:9090/api/v1/query?query=up{job=~"ai-lab-.*"}' | python3 -m json.tool
```

---

## 6. MÉTRICAS DISPONIBLES

### Node Exporter (:9100 — 1,334 métricas)

| Métrica clave | Descripción |
|--------------|-------------|
| `node_cpu_seconds_total` | Tiempo de CPU por modo |
| `node_load1` | Load average 1 min |
| `node_memory_MemTotal_bytes` | RAM total |
| `node_memory_MemAvailable_bytes` | RAM disponible |
| `node_filesystem_size_bytes` | Tamaño de disco |
| `node_filesystem_avail_bytes` | Disco disponible |
| `node_network_receive_bytes_total` | Tráfico de red recibido |
| `node_systemd_units_state` | Estado de servicios systemd |

### unpoller / UniFi (:9130 — 3,682 métricas)

Corregido el 13/05/2026: apuntaba a `unifi.ui.com` (cloud) con API key. Se cambió a local (`192.168.1.1`) con usuario `opencode-agent`.

| Métrica | Descripción |
|---------|-------------|
| `unpoller_up` | Estado del poller |
| `unifi_site_*` | Métricas por sitio (clients, devices, throughput) |
| `unifi_device_*` | Métricas por dispositivo (APs, switch, gateway) |
| `unifi_client_*` | Métricas por cliente WiFi (signal, rx/tx, uptime) |

**Datos recolectados:** 1 sitio, 19 clientes, 2 UAP, 1 UDM, 1 USW, 3.167 métricas sin errores.

### cAdvisor (:8081 — 918 métricas)

| Métrica clave | Descripción |
|--------------|-------------|
| `container_cpu_usage_seconds_total{name="ollama"}` | CPU del contenedor Ollama |
| `container_memory_working_set_bytes{name="qdrant"}` | RAM del contenedor Qdrant |
| `container_network_receive_bytes_total{name="traefik"}` | Red de Traefik |
| `container_fs_usage_bytes{name="open-webui"}` | Disco usado por Open WebUI |

### Ollama (:11434)

> ⚠️ No disponible. Ollama v0.23.2 no expone métricas. Requiere actualizar Ollama a una versión más reciente.

---

## 6.5. DASHBOARDS MIGRADOS DESDE GRAFANA CLOUD

El 13/05/2026 se migraron 6 dashboards desde `labrazahome.grafana.net` a Grafana local:

| Dashboard | UID | Datasource | Propósito |
|-----------|-----|------------|-----------|
| **Labrazahome — Logs** | al6k9h6 | Loki (.40:3100) | Logs centralizados Alloy (Docker, journald, Nginx, WordPress, UniFi) |
| **Labrazahome — Time-Series Analysis** | alpt7gt | Prometheus + Loki | Análisis temporal de métricas |
| **UniFi Access Points WiFi** | al79ptk | Prometheus (.40) | Puntos de acceso UniFi |
| **UniFi Cloud Gateway Fiber** | alw8vm9 | Prometheus (.40) | Gateway UniFi Cloud |
| **UniFi Switch USW Flex 2.5G 8 PoE** | al2m9l8 | Prometheus (.40) | Switch UniFi |
| **Windows Server - NAS N5** | aldh6t8 | Prometheus (.40) | NAS-N5 Windows 11 Pro (Alloy + windows_exporter) |

**Detalles técnicos:**
- Se reemplazaron los datasources de Grafana Cloud (`grafanacloud-prom`, `grafanacloud-logs`, `grafanacloud-ml-metrics`) por los locales
- Los archivos se almacenan en `grafana/provisioning/dashboards/migrated/` para provisioning automático
- API Key usada: `GRAFANA_SERVICE_ACCOUNT_TOKEN_REDACTED` (labrazahome.grafana.net)

---

## 6.6. PROMTAIL — LOGS A LOKI

### despliegue
- **Contenedor:** `promtail` en Ubuntu (.30)
- **Imagen:** `grafana/promtail:3.4.2`
- **Stack:** `/opt/ai-lab/stacks/promtail/docker-compose.yml`
- **Config:** `/opt/ai-lab/stacks/promtail/promtail.yml`

### Fuentes de logs configuradas

| Job | Método | Contenido |
|-----|--------|-----------|
| **docker** | Docker service discovery via socket | Logs de todos los contenedores (traefik, ollama, qdrant, open-webui, portainer, grafana, node-exporter, cadvisor) |
| **journald** | Lectura de `/var/log/journal` | Logs del sistema Ubuntu (systemd, sshd, cron, kernel) |
| **unifi-ids** | Syslog UDP `:1514` → RFC5424 | Eventos de seguridad del Cloud Gateway Fiber (IDS/IPS) |

### Correcciones aplicadas

1. **Docker logs:** inicialmente rechazados por Loki por timestamps antiguos (previos al deploy). Resuelto automáticamente tras el primer purge.
2. **Syslog IDS:** Promtail espera RFC5424 por defecto. UniFi Gateway configurado para enviar a `192.168.1.30:1514` UDP.

### Origen de los logs

```
UniFi Gateway (.1)                        NAS-N5 (.250)
       │                                        │
       │ IDS events                            │ Windows eventlog
       ▼                                        ▼
┌─────────────────┐                   ┌─────────────────┐
│ Promtail :1514   │                   │   Alloy         │
│ UDP → Loki       │                   │ → Loki (.40)    │
└────────┬────────┘                   └────────┬────────┘
         │                                     │
         ▼                                     ▼
    ┌──────────────────────────────────────────────┐
    │               Loki (.40:3100)                  │
    │  jobs: docker, journald, unifi-ids,            │
    │        windows-eventlog                         │
    └──────────────────────┬─────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Grafana    │
                    │  Dashboards  │
                    └──────────────┘
```

---

## 6.7. INVENTARIO DE RED — ESCANEO COMPLETO

El 13/05/2026 se realizó escaneo de infraestructura via API UniFi + nmap.

### Dispositivos de red UniFi

| Dispositivo | IP | Modelo | Rol |
|-------------|-----|--------|-----|
| Cloud Gateway Fiber Labraza | 192.168.1.1 | UDMA6A8 | Gateway/router |
| USW Flex 2.5G 8 PoE | 192.168.1.2 | USWED37 | Switch gestionado |
| U7 Lite | 192.168.1.3 | UAPA693 | Access Point WiFi 7 |
| U7 In-Wall | 192.168.1.4 | UAPA6A5 | Access Point empotrado |

### Servidores y VMs (LAN 192.168.1.x)

| Host | IP | Rol |
|------|-----|-----|
| ubuntu-ialab | **192.168.1.30** | 🟢 AI-LAB orquestador |
| ubuntu-server | **192.168.1.40** | 🟢 Prometheus + Loki + servicios |
| X870EAORUSPRO | **192.168.1.50** | 🟢 Gaming PC RX9070 (nodo IA multimodal) |
| X870AORUSELITE | **192.168.1.60** | 🟢 Gaming PC RX7900XT (nodo IA razonamiento) |
| NAS-N5 | **192.168.1.250 / .200** | 🟢 Windows 11 Pro (Hyper-V + Alloy) |
| VM Serv2025-market | **192.168.1.150** | 🟢 Windows Server 2025 |
| VM Serv2025-hyperv2 | **192.168.1.100** | 🟢 Windows Server 2025 |
| NAS-N5 (nodo IA ligero) | **192.168.1.250** | 🟢 LM Studio + Router IA |

### Clientes WiFi activos (19 total)

| Cliente | IP | Red | Señal |
|---------|-----|-----|-------|
| Lenovo-Tab-M10-3rd-Gen | 192.168.1.175 | LAN | -42 dBm |
| Redmi-Note-9-Pro | 192.168.1.68 | LAN | -70 dBm |
| NAS-N5 | 192.168.1.200/.250 | LAN (cable) | — |
| Xiaomi Roborock | 192.168.10.220 | IoT | -42 dBm |
| Chromecast | 192.168.10.247 | IoT | -50 dBm |
| yeelink-light-strip2 (×2) | 192.168.10.32/.97 | IoT | -40/-50 dBm |
| dmaker-fan-p33 | 192.168.10.49 | IoT | -44 dBm |
| Samsung TV | 192.168.10.71 | IoT | — |
| Redmi-Note-12 | 192.168.2.60 | Guest? | -63 dBm |
| A33de-albertgraciaferret | 192.168.2.222 | Guest? | -46 dBm |

---

## 7. ESPECIFICACIONES TÉCNICAS

### Versiones fijas (sin latest)

| Imagen | Versión | Razón |
|--------|---------|-------|
| grafana/grafana | **12.0.2** | Estable, evita breaking changes |
| prom/node-exporter | **v1.9.1** | Última versión estable conocida |
| cadvisor | **v0.52.1** | Compatible con Docker moderno |

### Healthchecks

| Contenedor | Test | Intervalo |
|-----------|------|-----------|
| Grafana | `wget http://localhost:3000/api/health` | 30s |

### Labels consistentes

Todos los contenedores tienen:
```yaml
labels:
  env: homelab
  cluster: ai-lab
  role: observability/system/containers
```

### Timezone

- `TZ: Europe/Madrid` en todos los contenedores

### Seguridad

- `GF_SECURITY_ADMIN_PASSWORD: "19682507"`
- `GF_USERS_ALLOW_SIGN_UP: "false"`
- Sin registro público en Grafana

---

## 8. CONSUMO DE RECURSOS

| Servicio | RAM | Disco | CPU |
|----------|-----|-------|-----|
| Grafana | ~80 MB | ~500 MB (DB) | Bajo |
| Node Exporter | ~20 MB | ~30 MB | Muy bajo |
| cAdvisor | ~40 MB | ~100 MB | Bajo |
| **Total** | **~140 MB** | **~630 MB** | **Mínimo** |

---

## 9. UBICACIÓN DE ARCHIVOS

| Archivo | Ruta |
|---------|------|
| docker-compose | `/opt/ai-lab/stacks/observability/docker-compose.yml` |
| Datasources | `/opt/ai-lab/stacks/observability/grafana/provisioning/datasources/datasources.yml` |
| Dashboards provisioning | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/dashboards.yml` |
| Dashboard Node Exporter | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/node-exporter-full.json` |
| Dashboard cAdvisor | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/cadvisor-metrics.json` |
| Dashboard Labrazahome — Logs | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/al6k9h6.json` |
| Dashboard Labrazahome — Time-Series | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/alpt7gt.json` |
| Dashboard UniFi Access Points | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/al79ptk.json` |
| Dashboard UniFi Cloud Gateway | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/alw8vm9.json` |
| Dashboard UniFi Switch | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/al2m9l8.json` |
| Dashboard Windows Server NAS N5 | `/opt/ai-lab/stacks/observability/grafana/provisioning/dashboards/migrated/aldh6t8.json` |
| Datos Grafana | `/opt/ai-lab/stacks/observability/grafana/data/` |
| Este informe | `docs/opencode/09-observabilidad.md` |

---

## 10. ROLLBACK

Si es necesario deshacer la implementación:

```bash
# Detener y eliminar contenedores
cd /opt/ai-lab/stacks/observability && docker compose down

# Eliminar directorio
rm -rf /opt/ai-lab/stacks/observability

# Eliminar targets de prometheus.yml en VM .40
# (editar archivo y recargar Prometheus)

# Restaurar punto de control previo
cp -r /opt/ai-lab/snapshots/pre-observability-20260513_140622/stacks.backup /opt/ai-lab/stacks
```

---

## 11. PRÓXIMOS PASOS (PHASE 7)

| Componente | Estado |
|-----------|--------|
| Blackbox Exporter (ping, HTTP, TCP checks) | 📋 Planificado |
| Alertmanager (notificaciones) | 📋 Planificado |
| GPU exporters (AMD RX7900XT, RX9070 vía WMI) | 📋 Planificado |
| Dashboard personalizado AI-LAB (estado clúster cognitivo) | 📋 Planificado |
| Alertas de infraestructura (disco, RAM, latencia) | 📋 Planificado |
| Grafana vía Traefik (HTTPS + dominio) | 📋 Planificado |

---

## 12. ACCESOS RÁPIDOS

| Servicio | URL |
|----------|-----|
| **Grafana** | http://192.168.1.30:3001 (admin / 19682507) |
| **Prometheus** | http://192.168.1.40:9090 |
| **Prometheus Targets** | http://192.168.1.40:9090/targets |
| **Open WebUI** | http://192.168.1.30:3000 |
| **Portainer** | http://192.168.1.30:9000 |
| **Loki** | http://192.168.1.40:3100 |
| **Promtail** | .30:1514/udp (syslog IDS) / .30 (Docker + journald) |
| **unpoller** | http://192.168.1.40:9130 |
| **Dozzle** | http://192.168.1.40:8080 |
