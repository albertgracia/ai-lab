# ANYTHINGLLM-LAN-ENABLE-01: LAN Exposure

**Estado:** ⏹ PENDING — requiere ejecución manual en .50
**Fecha:** 2026-07-04
**HEAD:** d92cc92

---

## 1. Análisis Previo (Source Code)

Se analizó el código fuente de AnythingLLM (tag `master`, commit `732eac6f`) para determinar cómo controla el bind address.

### 1.1 server/utils/boot/index.js

```js
function bootHTTP(app, port = 3001) {
  app.listen(port, async () => { ... });
  // Equivalent to app.listen(port, '0.0.0.0', ...)
}
```

`app.listen(port)` sin argumento host equivale a `0.0.0.0` (todas las interfaces) en Node.js/Express.

### 1.2 server/index.js

```js
if (!process.env.ENABLE_HTTPS) bootHTTP(app, process.env.SERVER_PORT || 3001);
```

No hay variable de entorno para el bind address. Solo `SERVER_PORT` para el puerto.

### 1.3 Desktop vs Server

| Versión | Comportamiento por defecto | Fuente |
|---------|---------------------------|--------|
| **Desktop (Electron)** | 127.0.0.1 | GitHub Security Advisory GHSA-24qj-pw4h-3jmm |
| **Bare metal / Docker** | 0.0.0.0 | `app.listen(port)` → Express default |

### 1.4 Conclusión

- Si AnythingLLM en .50 es la versión **Desktop**: el bind está en el wrapper Electron.
- Si es **bare metal** (Node.js directo): `app.listen(port)` ya escucha en `0.0.0.0` — el "Connection refused" desde fuera sería culpa del **Firewall de Windows**, no del bind.
- Si es **Docker**: el bind lo controla `docker run -p` o `docker-compose ports`.

---

## 2. Plan de Ejecución (desde .50)

### 2.1 Diagnosticar instalación

```powershell
# ¿Dónde está instalado AnythingLLM?
Get-Process | Where-Object { $_.ProcessName -like "*anything*" } | Format-Table Id, ProcessName, Path

# Si es Node.js:
Get-Process node* | Format-Table Id, ProcessName, CommandLine
# (usar: wmic process where "name='node.exe'" get commandline)
```

### 2.2 Determinar versión

| Síntoma | Versión | Acción |
|---------|---------|--------|
| `anythingllm-desktop.exe` o similar | Desktop | Buscar config en Electron |
| `node index.js` | Bare metal | Ya escucha en 0.0.0.0 → solo firewall |
| `docker ps \| find "anythingllm"` | Docker | Cambiar `-p 127.0.0.1:3001:3001` → `-p 3001:3001` |

### 2.3 Modificar bind

#### Caso A: Bare metal (más probable)

No hace falta cambiar bind. `app.listen(port)` ya escucha en `0.0.0.0`. **Solo firewall.**

#### Caso B: Desktop (Electron)

Buscar archivo de configuración del Electron wrapper:
```powershell
# Típicamente en %APPDATA%/anythingllm/ o en el directorio de instalación
Get-ChildItem -Recurse -Filter "*.js" -Path "$env:LOCALAPPDATA\Programs\anythingllm" | Select-String "listen"
```

O modificar directamente en el `.env` del servidor:
```powershell
# Si tiene un .env accesible
notepad "$env:PROGRAMDATA\anythingllm\server\.env"
# Añadir: no hay variable de bind, tocar server/utils/boot/index.js
```

#### Caso C: Docker

```powershell
# Verificar mapeo actual
docker inspect anythingllm | findstr "3001"

# Si muestra 127.0.0.1:3001 -> cambiar compose / run
docker stop anythingllm
docker rm anythingllm
docker run -d -p 3001:3001 ... # sin 127.0.0.1:
```

### 2.4 Firewall de Windows

```powershell
# Crear regla para LAN AI-LAB (192.168.1.0/24)
New-NetFirewallRule -DisplayName "AnythingLLM LAN AI-LAB" `
  -Direction Inbound `
  -Protocol TCP `
  -LocalPort 3001 `
  -RemoteAddress 192.168.1.0/24 `
  -Action Allow `
  -Profile Private,Domain

# Verificar regla
Get-NetFirewallRule -DisplayName "AnythingLLM LAN AI-LAB" | Format-Table DisplayName, Enabled, Action

# Ver reglas existentes en puerto 3001
Get-NetFirewallRule | Where-Object { $_.Description -like "*3001*" }
```

### 2.5 Reiniciar AnythingLLM

```powershell
# Si es servicio de Windows
Get-Service | Where-Object { $_.Name -like "*anything*" }
Restart-Service -Name "anythingllm"  # o el nombre correcto

# Si es proceso manual
Get-Process | Where-Object { $_.ProcessName -like "*node*" } | Stop-Process
# Luego reiniciar manualmente
```

---

## 3. Validación

### 3.1 Desde .50 (localhost)
```powershell
curl.exe -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3001
# → 200 OK
curl.exe -s -o /dev/null -w "%{http_code}" http://192.168.1.50:3001
# → 200 OK (confirma bind a 0.0.0.0)
```

### 3.2 Desde otro nodo (ej: NAS-N5 .200, control-plane .30)
```powershell
curl.exe -s -o /dev/null -w "%{http_code}" http://192.168.1.50:3001
# → 200 OK
```

### 3.3 Checklist completo

| # | Item | Método | Expected |
|---|------|--------|----------|
| 1 | UI accesible desde .50 | `curl 127.0.0.1:3001` | HTML |
| 2 | UI accesible desde LAN | `curl 192.168.1.50:3001` (otro nodo) | HTML |
| 3 | API responde | `curl 192.168.1.50:3001/api/ping` | JSON |
| 4 | Login funciona | Navegador a `http://192.168.1.50:3001` | Formulario login |
| 5 | LM Studio intacto | `curl 127.0.0.1:1234/v1/models` | 6 modelos |
| 6 | Providers unchanged | UI Settings → LLM / Embeddings | qwen2.5-14b + nomic/all-MiniLM |
| 7 | Sin exposición a Internet | Puerto 3001 no accesible desde fuera de LAN | ✅ |
| 8 | LM Studio no expuesto por error | `curl 192.168.1.50:1234/v1/models` (desde otro nodo) | ✅ sin cambios |
| 9 | AnythingLLM no modifica nada más | Verificar configuración pre/post | Sin cambios |

---

## 4. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|:-----------:|:-------:|------------|
| Exponer LM Studio accidentalmente | Baja | Alto | Solo cambiar bind de AnythingLLM, no tocar LM Studio |
| Firewall demasiado permisivo | Media | Alto | Restringir a `192.168.1.0/24`, no `0.0.0.0` |
| CORS policy demasiado abierta | Alta | Medio | AnythingLLM usa `cors({ origin: true })` por defecto — acepta cualquier origen. No cambiar. Dentro de LAN es aceptable. |
| Perder config actual | Baja | Alto | Hacer backup del `.env` antes de cambios |
| AnythingLLM deja de responder | Baja | Crítico (si hay docs cargados) | Rollback inmediato |

---

## 5. Rollback

### 5.1 Restaurar firewall
```powershell
Remove-NetFirewallRule -DisplayName "AnythingLLM LAN AI-LAB"
```

### 5.2 Restaurar bind (solo si se modificó)
- **Bare metal:** No requiere cambio (ya es `0.0.0.0` por defecto).
- **Desktop:** Revertir cambio en Electron wrapper.
- **Docker:** Volver a `-p 127.0.0.1:3001:3001`.

### 5.3 Verificar rollback
```powershell
# Desde otro nodo — debe fallar
curl.exe -s --connect-timeout 5 http://192.168.1.50:3001
# → Connection refused (o timeout) ✅

# Desde .50 — debe funcionar
curl.exe -s http://127.0.0.1:3001
# → HTML ✅
```

**Rollback no toca:** LM Studio, AI-LAB runtime, Hermes, Marketplace, Grafana, .30, providers.

---

## 6. Archivos relevantes

| Archivo | Propósito |
|---------|-----------|
| `server/utils/boot/index.js` | `bootHTTP()` llama `app.listen(port)` sin host → 0.0.0.0 |
| `server/index.js` | Punto de entrada, llama `bootHTTP(app, SERVER_PORT \|\| 3001)` |
| `server/.env` | Config server (`SERVER_PORT`, `JWT_SECRET`, `STORAGE_DIR`) |
| `frontend/.env` | Config frontend (`VITE_API_BASE`) |

No existe variable de entorno para bind address en AnythingLLM. Si se requiere cambiarlo, tocar `server/utils/boot/index.js`:
```js
// Antes:
app.listen(port, async () => { ... });
// Después (si se necesita 127.0.0.1 explícito):
app.listen(port, '0.0.0.0', async () => { ... });
//                                    ^^^^^^^^ ya implícito, pero explícito no daña
```
