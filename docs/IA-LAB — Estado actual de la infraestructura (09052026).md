IA-LAB — Estado actual de la infraestructura (09/05/2026)
Visión general

La plataforma IA-LAB ya dispone de una arquitectura híbrida distribuida funcional compuesta por:

Nodo Linux principal de orquestación (ubuntu-ialab)
2 nodos Windows GPU accesibles vía SSH
LM Studio distribuido
Runtime Python para telemetría
Docker stacks operativos
Open WebUI
Qdrant
Traefik
Portainer
Sistema de estado GPU en tiempo real
Acceso remoto sin password mediante claves SSH
Arquitectura actual
Nodo principal Linux

Host principal:

ubuntu-ialab
192.168.1.30


Funciones:

Orquestador central
Runtime Python
Docker host
Monitoring
Routing
Open WebUI
Ollama
Qdrant
Traefik
Portainer

Ruta principal:

/opt/ai-lab

Nodos GPU Windows
Nodo RX9070XT

Hostname: X870EAORUSPRO
IP: 192.168.1.50
GPU: RX 9070 XT
VRAM: 16 GB
Usuario SSH: ailab


Modelos LM Studio:

qwen3-14b-claude-sonnet-4.5-reasoning-distill
google/gemma-4-e4b
deepseek-r1-qwen3-8b
nomic-embed-text-v1.5

Nodo RX7900XT

Hostname: X870AORUSELITE
IP: 192.168.1.60
GPU: RX 7900 XT
VRAM: 20 GB
Usuario SSH: ailab

Modelos LM Studio:

qwen2.5-coder-14b
qwen2.5-coder-32b
deepseek-r1
gemma-4-26b
flux
moondream2
embeddings nomic


Estado SSH distribuido
Objetivo conseguido

Acceso remoto automático desde Linux hacia Windows SIN password.

Claves SSH

Generadas en:

/opt/ai-lab/key_saved
/opt/ai-lab/key_saved.pub
ED25519

Comando validado
ssh -i /opt/ai-lab/key_saved \
  -o IdentitiesOnly=yes \
  -o PreferredAuthentications=publickey \
  ailab@192.168.1.50 "hostname"
 

 Resultado:
  X870EAORUSPRO
  
  Configuración Windows OpenSSH
Problema detectado

Windows NO estaba usando:

C:\Users\ailab\.ssh\authorized_keys
Porque el usuario pertenece al grupo Administradores.


Solución funcional

Archivo correcto:

C:\ProgramData\ssh\administrators_authorized_keys


Permisos necesarios

PowerShell Admin:

icacls C:\ProgramData\ssh\administrators_authorized_keys /inheritance:r

icacls C:\ProgramData\ssh\administrators_authorized_keys /grant "SYSTEM:F"

icacls C:\ProgramData\ssh\administrators_authorized_keys /grant "Administradores:F"

Reinicio servicio SSH
Restart-Service sshd

Runtime GPU
Archivo principal

runtime/state/gpu_state.py

Funciones:

conexión SSH distribuida
lectura typeperf Windows
parsing CSV
telemetría GPU
VRAM usage
detección engines activos

Problema importante resuelto
Error UTF-8

Error original:

UnicodeDecodeError: 'utf-8' codec can't decode byte 0xa0


Causa

typeperf en Windows devuelve CP1252.

Solución

encoding="cp1252",
errors="ignore"

Métricas GPU actuales
RX9070XT

Estado:

GPU prácticamente idle
VRAM usada ~12.4 GB
VRAM libre ~3.6 GB
RX7900XT

Estado:

GPU prácticamente idle
VRAM usada ~13 GB
VRAM libre ~7 GB
Runtime global
Archivo

runtime/state/system_state.py

Integra:

docker
llm
gpu
nodos remotos
Docker stacks operativos
Infraestructura activa
Servicio	Estado
Traefik	OK
Qdrant	OK
Open WebUI	OK
Ollama	OK
Portainer	OK


URLs internas

Open WebUI

http://openwebui.local

3000

http://portainer.local

9000

http://qdrant.local

6333


Objetivo siguiente — OpenCode
Próxima fase

Integrar OpenCode como:

director de orquesta
planner multiagente
router cognitivo
executor
reasoning coordinator


Diseño previsto OpenCode
Roles posibles
Función	Modelo
Orquestador	qwen3-14b
Coding	qwen2.5-coder-32b
Fast reasoning	gemma-4
Embeddings	nomic
Vision	moondream2
Imagen	flux


Objetivos de routing

Runtime deberá decidir:

nodo
modelo
prioridad
latencia
VRAM libre
especialización
tamaño contexto


Problemas esperables

Muy probables durante integración:


context overflow
tool recursion
agent loops
timeouts
routing incorrecto
hallucinated tool calls

Esto ya forma parte normal de una arquitectura multiagente real.


Estado actual del proyecto
Estado REAL

La infraestructura ya NO es un laboratorio experimental simple.

Actualmente IA-LAB ya dispone de:

inferencia distribuida
runtime centralizado
observabilidad GPU
orchestration base
federation LM Studio
routing potencial
telemetría real
acceso remoto automatizado

La siguiente fase ya entra en:


Distributed Cognitive Architecture Engineering