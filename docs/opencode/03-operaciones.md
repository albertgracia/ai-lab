# AI-LAB: GUÍA DE OPERACIONES Y ADMINISTRACIÓN
## Mantenimiento, monitoreo y gestión diaria

---

## 1. GESTIÓN DE CONTENEDORES DOCKER

### 1.1. Servicios Activos

| Servicio | Directorio docker-compose |
|----------|---------------------------|
| Traefik | `/opt/ai-lab/stacks/traefik/` |
| Open WebUI + Ollama | `/opt/ai-lab/stacks/ai-core/` |
| Qdrant | `/opt/ai-lab/stacks/qdrant/` |
| Portainer | `/opt/ai-lab/stacks/portainer/` |

### 1.2. Comandos Comunes

```bash
# Ver estado de todos los contenedores
docker ps

# Logs de un servicio
docker logs traefik --tail 50
docker logs open-webui --tail 50
docker logs qdrant --tail 50
docker logs ollama --tail 50

# Ver consumo de recursos
docker stats --no-stream

# Reiniciar un servicio
docker compose -f /opt/ai-lab/stacks/traefik/docker-compose.yml restart
docker compose -f /opt/ai-lab/stacks/ai-core/docker-compose.yml restart

# Actualizar imágenes
docker compose -f /opt/ai-lab/stacks/ai-core/docker-compose.yml pull
docker compose -f /opt/ai-lab/stacks/ai-core/docker-compose.yml up -d

# Inspeccionar red
docker network ls
docker network inspect proxy
```

### 1.3. Acceso a Portainer
```
URL: http://192.168.1.30:9000
```
Gestión visual de contenedores, volúmenes, redes y stacks.

---

## 2. ACCESO A LOS NODOS

### 2.1. Nodo Principal (Ubuntu)
```bash
# SSH local
ssh albert@192.168.1.30

# Rutas importantes
/opt/ai-lab/          # Repositorio principal
/opt/ai-lab/runtime/  # Código del runtime
/opt/ai-lab/stacks/   # Docker compose stacks
/mnt/ai-models/       # Modelos de IA
/var/log/             # Logs del sistema
```

### 2.2. Nodos GPU (Windows)
Conexión SSH con clave privada:
```bash
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.60   # RX7900XT
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.50   # RX9070
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.250  # NAS
```

Estado GPU vía SSH:
```bash
# Uso de GPU (typeperf)
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.60 'typeperf "\GPU Engine(*)\Utilization Percentage" -sc 1'

# VRAM
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.60 'typeperf "\GPU Adapter Memory(*)\Dedicated Usage" -sc 1'
```

---

## 3. GESTIÓN DE MODELOS

### 3.1. Ollama (CPU Local)
```bash
# Listar modelos
ollama list

# Descargar modelo
ollama pull qwen2.5:7b

# Eliminar modelo
ollama rm qwen2.5:7b

# API directa
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b","prompt":"Hola"}'
```

### 3.2. LM Studio (GPU - Nodos Remotos)
Los modelos se gestionan desde la interfaz gráfica de LM Studio en cada nodo Windows.

```bash
# Ver modelos disponibles en cada nodo
curl http://192.168.1.60:1234/v1/models
curl http://192.168.1.50:1234/v1/models
curl http://192.168.1.250:1234/v1/models
```

---

## 4. GESTIÓN DE MEMORIA

### 4.1. Qdrant (Base Vectorial)
```bash
# Colecciones disponibles
curl http://localhost:6333/collections

# Detalles de colección
curl http://localhost:6333/collections/ai_lab_memory
curl http://localhost:6333/collections/agent_knowledge

# Número de puntos
curl http://localhost:6333/collections/ai_lab_memory | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['points_count'])"
```

### 4.2. Memoria Episódica
```bash
# Ver últimos episodios
tail -5 /opt/ai-lab/runtime/state/episodic_memory.jsonl | python3 -m json.tool

# Contar episodios
wc -l /opt/ai-lab/runtime/state/episodic_memory.jsonl

# Ver auditoría
tail -3 /opt/ai-lab/runtime/state/governance_audit.jsonl | python3 -m json.tool
```

### 4.3. Reindexar Conocimiento
```bash
# Pipeline de embeddings
python3 /opt/ai-lab/runtime/rag/embedding_pipeline.py

# Indexar agentes en Qdrant
python3 /opt/ai-lab/runtime/indexer/index_agent.py
```

---

## 5. SNAPSHOTS Y RESPALDOS

### 5.1. Snapshot de Estado del Sistema
```bash
# Generar snapshot manual
python3 /opt/ai-lab/runtime/state/system_state.py

# El snapshot se guarda en:
# /opt/ai-lab/runtime/state/system_snapshot.json
```

### 5.2. Live State (Loop Continuo)
```bash
# Iniciar loop de snapshots cada 5s (historial cada 60s)
python3 /opt/ai-lab/runtime/state/live_state.py
```

### 5.3. Directorios a Respaldar

| Directorio | Prioridad | Frecuencia recomendada |
|------------|-----------|------------------------|
| `/opt/ai-lab/` (sin datasets) | 🔴 Alta | Diaria (git) |
| `/opt/ai-lab/runtime/state/` | 🔴 Alta | Diaria |
| `/opt/ai-lab/runtime/nodes/nodes.json` | 🟡 Media | Semanal |
| `/mnt/ai-models/` | 🟢 Baja | Solo si se descargan nuevos |
| `/opt/ai-lab/memory/` | 🟡 Media | Semanal |

---

## 6. MONITOREO

### 6.1. Comandos Rápidos

```bash
# Estado general del sistema
uptime && free -h && df -h /

# Carga del sistema
htop  # o top

# Discos
df -h / /mnt/ai-models

# Espacio en /opt/ai-lab
du -sh /opt/ai-lab/
du -sh /opt/ai-lab/runtime/state/

# Procesos Python del runtime
ps aux | grep python3 | grep -v grep

# Puertos en escucha
ss -tlnp | grep -E '8000|3000|9000|11434|6333'
```

### 6.2. Health Check del Clúster
```bash
python3 /opt/ai-lab/runtime/nodes/healthcheck.py
cat /opt/ai-lab/runtime/state/cluster_state.json
```

### 6.3. Stack de Observabilidad (Planificado)
Una vez instalado:
- **Grafana**: `http://192.168.1.30:3001`
- **Prometheus**: `http://192.168.1.30:9090`
- Dashboards preconfigurados para métricas del sistema

---

## 7. ACCESO A INTERFACES WEB

| Servicio | URL |
|----------|-----|
| Open WebUI | `http://192.168.1.30:3000` |
| Portainer | `http://192.168.1.30:9000` |
| Traefik Dashboard | `http://192.168.1.30:8080` |
| Qdrant UI | `http://192.168.1.30:6333/dashboard` |

---

## 8. SMB (COMPARTICIÓN DE ARCHIVOS)

### 8.1. Acceso desde Windows
```
\\192.168.1.30\ai-lab\      → /opt/ai-lab/ (usuario: albert)
```

### 8.2. Configuración Samba
```bash
# Ver configuración actual
cat /etc/samba/smb.conf

# Reiniciar servicio
sudo systemctl restart smbd
sudo systemctl status smbd

# Añadir usuario Samba
sudo smbpasswd -a albert
```

---

## 9. SOLUCIÓN DE PROBLEMAS COMUNES

### 9.1. Contenedor caído
```bash
docker ps -a | grep -E "traefik|open-webui|qdrant|ollama|portainer"
docker logs <nombre> --tail 50
docker compose -f /opt/ai-lab/stacks/<stack>/docker-compose.yml up -d
```

### 9.2. Nodo GPU no responde
```bash
# Verificar conectividad
ping 192.168.1.60

# Verificar LM Studio
curl http://192.168.1.60:1234/v1/models

# Si no responde: reiniciar LM Studio en el nodo Windows
```

### 9.3. Router API no disponible
```bash
# Iniciar manualmente
cd /opt/ai-lab && uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8000

# O como servicio systemd (cuando esté configurado):
sudo systemctl start ai-lab-router
sudo systemctl status ai-lab-router
```

### 9.4. Qdrant sin vectores
```bash
# Reindexar
python3 /opt/ai-lab/runtime/rag/embedding_pipeline.py
python3 /opt/ai-lab/runtime/indexer/index_agent.py
```

### 9.5. Espacio en disco bajo
```bash
# Limpiar imágenes Docker no usadas
docker system prune -a

# Revisar logs grandes
sudo journalctl --vacuum-size=200M

# Revisar modelos no necesarios en /mnt/ai-models/ollama/
```

---

## 10. CHECKLIST DIARIO

- [ ] `docker ps` — todos los contenedores UP
- [ ] `curl http://192.168.1.60:1234/v1/models` — RX7900XT responde
- [ ] `curl http://192.168.1.50:1234/v1/models` — RX9070 responde
- [ ] `curl http://192.168.1.250:1234/v1/models` — NAS responde
- [ ] `df -h /` — disco root < 80%
- [ ] `free -h` — RAM disponible suficiente
- [ ] `ping -c 1 192.168.1.60` — latencia < 5ms
- [ ] Estado GPU (`python3 -m runtime.state.system_state`)
