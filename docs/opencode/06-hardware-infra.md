# AI-LAB: REFERENCIA DE HARDWARE E INFRAESTRUCTURA
## Especificaciones, benchmarks, redes y capacidad

---

## 1. INVENTARIO DE HARDWARE

### 1.1. Nodo Principal (Orquestación)

| Componente | Detalle |
|------------|---------|
| **Hostname** | ubuntu-ialab |
| **IP** | 192.168.1.30 |
| **OS** | Ubuntu Server 26.04 LTS (Resolute) |
| **Virtualización** | Hyper-V |
| **RAM** | 7.2 GB |
| **Swap** | 4.0 GB |
| **Disco root** | 97 GB (53 GB libres — 55%) |
| **Disco modelos** | 79 GB (70 GB libres — 89%) |
| **CPU** | (sin datos específicos) |

### 1.2. NAS Local Router

| Componente | Detalle |
|------------|---------|
| **Hostname** | (NAS local) |
| **IP** | 192.168.1.250 |
| **GPU** | AMD Radeon RX780M (iGPU) |
| **VRAM** | 0.75 GB (compartida) |
| **Backend** | LM Studio |
| **Prioridad** | 1 |
| **Capacidades** | fast, lightweight, fallback, router, memory |

### 1.3. RX7900XT Reasoning Node

| Componente | Detalle |
|------------|---------|
| **Hostname** | rx7900xt-node |
| **IP** | 192.168.1.60 |
| **GPU** | AMD Radeon RX7900XT |
| **VRAM** | 20 GB GDDR6 |
| **Backend** | LM Studio |
| **Prioridad** | 10 (máxima) |
| **Capacidades** | reasoning, coding, large-context, multi-agent, orchestration, backend |

### 1.4. RX9070 Multimodal Node

| Componente | Detalle |
|------------|---------|
| **Hostname** | rx9070-node |
| **IP** | 192.168.1.50 |
| **GPU** | AMD Radeon RX9070 |
| **VRAM** | 16 GB GDDR6 |
| **Backend** | LM Studio |
| **Prioridad** | 8 |
| **Capacidades** | vision, image, multimodal, embeddings, creative, frontend |

---

## 2. CAPACIDAD DE CÓMPUTO TOTAL

| Recurso | Total |
|---------|-------|
| GPUs | 3 (RX780M + RX7900XT + RX9070) |
| VRAM total | ~36.75 GB |
| Nodos de inferencia | 3 |
| Nodo de orquestación | 1 |

### 2.1. Capacidad Residual Actual

| Recurso | Total | Usado | Libre | % Libre |
|---------|-------|-------|-------|---------|
| RAM Ubuntu | 7.2 GB | 1.6 GB | 5.7 GB | 79% |
| Disco root | 97 GB | 40 GB | 53 GB | 55% |
| Disco modelos | 79 GB | 4.4 GB | 70 GB | 89% |
| VRAM RX9070 | 16 GB | 2.8 GB | 13.2 GB | 83% |
| VRAM RX7900XT | 20 GB | 19.0 GB | 1.0 GB | 5% ⚠️ |
| Carga CPU | — | 0.33 | — | Bajo |

---

## 3. BENCHMARKS

### 3.1. Latencia de Inferencia

Prueba: prompt "Responde solo: OK", 10 tokens max, temp 0.1

| Nodo | Modelo | Params | Tiempo | Throughput estimado |
|------|--------|--------|--------|---------------------|
| NAS (.250) | gemma-4-e4b | ~4B | 315 ms | ~32 req/min |
| RX7900XT (.60) | deepseek-r1-8b | 8B | 7,687 ms | ~8 req/min |
| RX7900XT (.60) | qwen3-14b-reasoning | 14B | 12,996 ms | ~5 req/min |
| RX7900XT (.60) | qwen2.5-coder-32b | 32B | 13,184 ms | ~5 req/min |
| RX7900XT (.60) | gemma-4-26b-a4b | 26B (MoE) | 41,250 ms | ~1.5 req/min |
| Ollama (CPU) | qwen2.5:7b | 7B | 10,980 ms | ~5 req/min |
| RX9070 (.50) | (todos) | — | Error 500 | ❌ |

### 3.2. VRAM por Modelo Cargado

| Nodo | Modelo(s) cargado(s) | VRAM usada | Capacidad |
|------|---------------------|------------|-----------|
| RX7900XT | qwen2.5-coder-32b + otros | 19.03 GB | 20 GB |
| RX9070 | — (error) | 2.76 GB | 16 GB |
| NAS | gemma-4-e4b | ~0.5 GB | 0.75 GB |

---

## 4. RED

### 4.1. Topología

```
                    ┌──────────────────┐
                    │   ubuntu-ialab   │
                    │   192.168.1.30   │
                    │   Orquestador    │
                    └───┬───┬───┬─────┘
                        │   │   │
              ┌─────────┘   │   └──────────┐
              ▼             ▼              ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │  NAS     │ │ RX7900XT │ │ RX9070   │
        │ .250     │ │ .60      │ │ .50      │
        │ RX780M   │ │ 20GB     │ │ 16GB     │
        │ Router   │ │Reasoning │ │Multimodal│
        └──────────┘ └──────────┘ └──────────┘
```

### 4.2. Latencias

| Ruta | Latencia | Packet Loss | Calificación |
|------|----------|-------------|-------------|
| ubuntu-ialab → RX7900XT | 0.53 ms | 0% | Excelente |
| ubuntu-ialab → RX9070 | 0.31 ms | 0% | Excelente |
| ubuntu-ialab → NAS | 0.39 ms | 0% | Excelente |
| RX7900XT → RX9070 | <1 ms (estimado) | — | Excelente |

### 4.3. Puertos Expuestos

| Puerto | Servicio | Nodo |
|--------|----------|------|
| 80 | HTTP (Traefik) | ubuntu-ialab |
| 443 | HTTPS (Traefik) | ubuntu-ialab |
| 3000 | Open WebUI | ubuntu-ialab |
| 9000 | Portainer | ubuntu-ialab |
| 6333 | Qdrant gRPC | ubuntu-ialab |
| 6334 | Qdrant HTTP | ubuntu-ialab |
| 8080 | Traefik Dashboard | ubuntu-ialab |
| 11434 | Ollama API | ubuntu-ialab |
| 1234 | LM Studio API | .50, .60, .250 |
| 445 | SMB | ubuntu-ialab |
| 22 | SSH | Todos |

---

## 5. ALMACENAMIENTO

### 5.1. Puntos de Montaje

| Punto | Tamaño | Uso | Contenido |
|-------|--------|-----|-----------|
| `/` (root) | 97 GB | 43% | Sistema + Runtime + Logs |
| `/mnt/ai-models` | 79 GB | 6% | Modelos Ollama, datasets |
| `/opt/ai-lab` | (en root) | — | Código, config, docs |

### 5.2. Distribución de /opt/ai-lab/

| Directorio | Tamaño | Propósito |
|------------|--------|-----------|
| `runtime/` | ~500 KB | Código Python |
| `stacks/` | ~50 KB | Docker compose |
| `.agent/` | ~1 MB | Agentes, skills, workflows |
| `memory/` | ~50 KB | Conocimiento local |
| `snapshots/` | ~5 MB | Snapshots de sistema |
| `data/` | Variable | Datos persistentes Docker |
| `docs/` | ~100 KB | Documentación |

### 5.3. Almacenamiento Docker

| Volumen | Tamaño | Contenido |
|---------|--------|-----------|
| Qdrant storage | ~449 MB (block I/O) | Vectores y puntos |
| Open WebUI data | ~2.39 GB (block I/O) | Configuración de usuarios |
| Ollama models | ~4.7 GB | Modelos descargados |

---

## 6. REDES DOCKER

```bash
# Redes disponibles
docker network ls

# Red proxy (usada por Traefik + servicios)
docker network inspect proxy
```

| Red | Driver | Propósito |
|-----|--------|-----------|
| `proxy` | bridge | Tráfico Traefik → servicios |
| `bridge` | bridge | Default Docker |

---

## 7. CONSUMOS ESTIMADOS

| Componente | Consumo estimado |
|------------|-----------------|
| ubuntu-ialab (idle) | ~50W |
| NAS (idle) | ~30W |
| RX7900XT (idle/inferencia) | ~50W / ~250W |
| RX9070 (idle/inferencia) | ~40W / ~200W |
| **Total estimado** | **~170W idle / ~530W full** |

> Medir consumo real con medidor de pared para datos precisos.

---

## 8. SERVIDORES Y SERVICIOS

### 8.1. Servicios del Sistema

| Servicio | Estado | Puerto |
|----------|--------|--------|
| smbd (Samba) | ✅ Running | 445 |
| nmbd (NetBIOS) | ✅ Running | 137-138 |
| sshd | ✅ Running | 22 |
| Docker | ✅ Running | socket |

### 8.2. Stack Docker

| Servicio | Imagen | Estado | Puertos |
|----------|--------|--------|---------|
| Traefik | traefik:latest | ✅ Up 16h | 80, 443, 8080 |
| Qdrant | qdrant/qdrant:latest | ✅ Up 27h | 6333-6334 |
| Open WebUI | open-webui:main | ✅ Up 27h | 3000 |
| Ollama | ollama/ollama:latest | ✅ Up 27h | 11434 |
| Portainer | portainer-ce:latest | ✅ Up 27h | 9000 |

---

## 9. MANTENIMIENTO DE HARDWARE

### 9.1. Tareas Periódicas

| Tarea | Frecuencia | Comando |
|-------|------------|---------|
| Verificar espacio en disco | Semanal | `df -h` |
| Limpiar Docker innecesario | Mensual | `docker system prune -a` |
| Actualizar imágenes Docker | Mensual | `docker compose pull` |
| Verificar estado nodos GPU | Diario | `curl http://<ip>:1234/v1/models` |
| Respaldar estado del sistema | Diario | Git commit + push |

### 9.2. Temperaturas

No hay monitoreo térmico instalado. Para añadirlo:

```bash
# En Ubuntu
sudo apt install lm-sensors -y
sudo sensors-detect

# En nodos Windows (vía SSH)
# Usar typeperf o herramientas como GPU-Z
```

---

## 10. PLAN DE CAPACIDAD

### 10.1. Cuello de Botella Actual

- **VRAM RX7900XT al 95%** — limitante principal. El modelo qwen2.5-coder-32b consume casi toda la VRAM disponible.

### 10.2. Recomendaciones de Expansión

1. Añadir más RAM al nodo Ubuntu (actualmente 7.2 GB — suficiente para el runtime pero limitado para cargas pesadas)
2. Añadir GPU adicional o nodo con más VRAM (48 GB+) para modelos >32B
3. Configurar almacenamiento en red (NAS) para modelos
4. Implementar monitoreo térmico en todos los nodos
