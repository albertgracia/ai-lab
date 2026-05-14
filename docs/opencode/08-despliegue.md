# AI-LAB: GUÍA DE DESPLIEGUE Y ONBOARDING
## Cómo desplegar desde cero y añadir nuevos nodos

---

## 1. REQUISITOS DEL SISTEMA

### 1.1. Nodo Principal (Orquestador)

**Mínimos:**
- Ubuntu Server 24.04+ o 26.04 LTS
- 4 GB RAM
- 50 GB disco
- Docker + Docker Compose
- Red local con IP fija

**Recomendados:**
- 8+ GB RAM
- 100+ GB SSD
- GPU dedicada (opcional)
- Acceso SSH configurado

### 1.2. Nodos de Inferencia (GPU)

**Mínimos:**
- Windows 10/11 o Linux
- GPU con 4+ GB VRAM
- LM Studio instalado
- Red local con IP fija
- SSH habilitado (Windows: OpenSSH Server)

**Recomendados:**
- GPU AMD/NVIDIA con 12+ GB VRAM
- Windows 11 Pro
- Conexión de red por cable (no WiFi)

---

## 2. INSTALACIÓN DEL NODO PRINCIPAL

### 2.1. Dependencias Base

```bash
# Docker
sudo apt update
sudo apt install docker.io docker-compose-v2 -y
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# Python (ya incluido en 26.04)
sudo apt install python3 python3-pip python3-venv -y

# Samba (opcional, para compartir archivos)
sudo apt install samba -y

# Utilidades
sudo apt install htop net-tools iperf3 lm-sensors git -y
```

### 2.2. Clonar el Repositorio

```bash
git clone <repo-url> /opt/ai-lab
cd /opt/ai-lab
```

### 2.3. Entorno Virtual Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn requests sentence-transformers qdrant-client
```

### 2.4. Desplegar Stack Docker

```bash
# Stack de infraestructura (Traefik)
docker compose -f stacks/traefik/docker-compose.yml up -d

# Stack AI Core (Ollama + Open WebUI)
docker compose -f stacks/ai-core/docker-compose.yml up -d

# Stack Qdrant
docker compose -f stacks/qdrant/docker-compose.yml up -d

# Stack Portainer
docker compose -f stacks/portainer/docker-compose.yml up -d
```

### 2.5. Configurar Samba

```bash
# Editar /etc/samba/smb.conf y añadir:
# [ai-lab]
#   path = /opt/ai-lab
#   browseable = yes
#   read only = no
#   valid users = albert

sudo smbpasswd -a albert  # Establecer contraseña SMB
sudo systemctl restart smbd
```

---

## 3. AÑADIR UN NODO DE INFERENCIA (LM STUDIO)

### 3.1. En el Nodo Windows

1. Instalar [LM Studio](https://lmstudio.ai/)
2. Descargar modelos desde la interfaz o Hugging Face
3. Habilitar el servidor API:
   - Settings → Local Server → Enable OpenAI-compatible API
   - Puerto recomendado: 1234
4. Habilitar OpenSSH Server:
   ```powershell
   Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```

### 3.2. Configurar Acceso SSH

```bash
# En el nodo Ubuntu, generar clave (si no existe)
ssh-keygen -t ed25519 -f /opt/ai-lab/key_saved -N ""

# Copiar clave al nodo Windows
ssh-copy-id -i /opt/ai-lab/key_saved.pub ailab@192.168.1.X
# O manualmente: copiar key_saved.pub a C:\Users\ailab\.ssh\authorized_keys
```

### 3.3. Registrar el Nodo

Editar `/opt/ai-lab/runtime/nodes/nodes.json`:

```json
{
  "name": "nuevo-nodo",
  "host": "192.168.1.X",
  "port": 1234,
  "backend": "lmstudio",
  "gpu": "Nombre GPU",
  "vram_gb": XX,
  "priority": 5,
  "enabled": true,
  "capabilities": ["nueva-capacidad"],
  "models": ["modelo-ejemplo"]
}
```

### 3.4. Probar Conexión

```bash
# Verificar que responde
curl http://192.168.1.X:1234/v1/models

# Verificar SSH
ssh -i /opt/ai-lab/key_saved ailab@192.168.1.X "hostname"
```

---

## 4. CONFIGURACIÓN DEL RUNTIME

### 4.1. Verificar Salud del Sistema

```bash
python3 /opt/ai-lab/runtime/nodes/healthcheck.py
cat /opt/ai-lab/runtime/state/cluster_state.json
```

### 4.2. Iniciar Router API (FastAPI)

```bash
# Como proceso
cd /opt/ai-lab
source .venv/bin/activate
uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8000 &

# Como servicio systemd (recomendado)
sudo tee /etc/systemd/system/ai-lab-router.service > /dev/null <<'EOF'
[Unit]
Description=AI-LAB Router API
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=albert
WorkingDirectory=/opt/ai-lab
ExecStart=/opt/ai-lab/.venv/bin/uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now ai-lab-router
```

### 4.3. Indexar Conocimiento en Qdrant

```bash
# Indexar archivos de memoria
python3 /opt/ai-lab/runtime/rag/embedding_pipeline.py

# Indexar agentes
python3 /opt/ai-lab/runtime/indexer/index_agent.py
```

---

## 5. VERIFICACIÓN POST-DESPLIEGUE

### 5.1. Checklist

- [ ] `docker ps` — 5 contenedores UP
- [ ] `curl http://localhost:11434/api/tags` — Ollama responde
- [ ] `curl http://localhost:6333/collections` — Qdrant responde
- [ ] `curl http://192.168.1.60:1234/v1/models` — RX7900XT responde
- [ ] `curl http://192.168.1.50:1234/v1/models` — RX9070 responde
- [ ] `curl http://192.168.1.250:1234/v1/models` — NAS responde
- [ ] `curl http://localhost:8000/health` — Router API OK
- [ ] `curl http://localhost:3000` — Open WebUI accesible
- [ ] `curl http://localhost:9000` — Portainer accesible
- [ ] `python3 runtime/state/system_state.py` — snapshot generado sin errores

### 5.2. Prueba de Inferencia

```bash
# Probar nodo NAS
curl http://192.168.1.250:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-4-e4b","messages":[{"role":"user","content":"Hola"}],"max_tokens":50}'

# Probar router API (una vez iniciado)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ailab-router/fast","messages":[{"role":"user","content":"Hola"}],"max_tokens":50}'
```

---

## 6. DESPLIEGUE DE MODELOS

### 6.1. En Ollama (CPU Local)

```bash
# Descargar modelo
ollama pull qwen2.5:7b

# Ver modelos instalados
ollama list

# Probar
ollama run qwen2.5:7b "Hola"
```

### 6.2. En LM Studio (GPU Remota)

Desde la interfaz gráfica de LM Studio en cada nodo:
1. Buscar modelo en la pestaña "Search"
2. Descargar
3. Cargar en la pestaña "Chat" o "Server"
4. Verificar que el servidor API está habilitado

---

## 7. CONFIGURACIÓN DE RED

### 7.1. IPs Fijas Recomendadas

| Dispositivo | IP | Propósito |
|-------------|-----|-----------|
| ubuntu-ialab | 192.168.1.30 | Orquestación |
| RX7900XT | 192.168.1.60 | Reasoning |
| RX9070 | 192.168.1.50 | Multimodal |
| NAS | 192.168.1.250 | Router ligero |

### 7.2. Firewall

```bash
# En Ubuntu (si aplica)
sudo ufw allow 22/tcp        # SSH
sudo ufw allow 80/tcp        # HTTP (Traefik)
sudo ufw allow 443/tcp       # HTTPS (Traefik)
sudo ufw allow 445/tcp       # SMB
sudo ufw allow from 192.168.1.0/24  # Red local
```

---

## 8. ACTUALIZACIÓN DEL SISTEMA

```bash
# Actualizar runtime (git pull)
cd /opt/ai-lab && git pull

# Actualizar servicios Docker
docker compose -f stacks/traefik/docker-compose.yml pull && docker compose up -d
docker compose -f stacks/ai-core/docker-compose.yml pull && docker compose up -d
docker compose -f stacks/qdrant/docker-compose.yml pull && docker compose up -d
docker compose -f stacks/portainer/docker-compose.yml pull && docker compose up -d

# Reindexar conocimiento
python3 /opt/ai-lab/runtime/rag/embedding_pipeline.py

# Reiniciar Router API
sudo systemctl restart ai-lab-router
```

---

## 9. SOLUCIÓN DE PROBLEMAS DE DESPLIEGUE

### 9.1. LM Studio no carga modelos
- Verificar suficiente VRAM libre
- Revisar logs de LM Studio (Help → View Logs)
- Probar modelo más pequeño

### 9.2. SSH no conecta a nodo Windows
- Verificar servicio SSH en Windows: `Get-Service sshd`
- Verificar firewall: `New-NetFirewallRule -DisplayName "SSH" -Direction Inbound -Protocol TCP -LocalPort 22 -Action Allow`

### 9.3. Docker no inicia
```bash
sudo systemctl status docker
sudo journalctl -u docker --tail 30
```

### 9.4. Router API no arranca
```bash
# Verificar dependencias Python
source /opt/ai-lab/.venv/bin/activate
pip install -r /opt/ai-lab/requirements.txt 2>/dev/null || \
pip install fastapi uvicorn requests

# Verificar sintaxis
python3 -m py_compile /opt/ai-lab/runtime/llm/router_api.py
```
