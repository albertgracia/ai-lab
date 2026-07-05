# RUNBOOK: ANYTHLLM-ENTERPRISE-03 — Create Workspaces

**Ejecutar en:** `.50` (RX9070) — RDP o terminal local
**API:** `http://127.0.0.1:3001/api`
**No cambiar bind. No exponer a LAN. No tocar Grafana. No tocar .30. No tocar AI-LAB runtime.**

---

## 1. Validación Previa

### 1.1 AnythingLLM local
```powershell
curl.exe -s http://127.0.0.1:3001
# → HTML page, AnythingLLM UI. Cualquier respuesta OK.
```

### 1.2 LM Studio local
```powershell
curl.exe -s http://127.0.0.1:1234/v1/models
# → JSON list. Debe incluir qwen2.5-14b-instruct y text-embedding-nomic-embed-text-v1.5
```

### 1.3 Obtener API key (si no la conoces)
```powershell
# En la UI de AnythingLLM: Settings → API Keys
# O si ya tienes una:
curl.exe -s http://127.0.0.1:3001/api/auth
```

---

## 2. Configurar Providers (UI)

Abrir `http://127.0.0.1:3001` en navegador local en `.50`.

### 2.1 LLM Provider → LM Studio
```
Settings → LLM Preference → Proveedores → LMStudio
```

| Campo | Valor |
|-------|-------|
| Modelo | `qwen2.5-14b-instruct` |
| Max Tokens | `4096` |
| Token Context | `4096` |
| Endpoint | `http://127.0.0.1:1234/v1` |

### 2.2 Embedding Provider → Built-in o LM Studio
```
Settings → Embedding Preference
```

| Prioridad | Provider | Modelo | Notas |
|-----------|----------|--------|-------|
| 1ª opción | LM Studio | `text-embedding-nomic-embed-text-v1.5` | Si AnythingLLM v13 lo soporta como provider OpenAI-compatible |
| Fallback | Built-in | `all-MiniLM-L6-v2` | Sin dependencias externas, 384 dims |

---

## 3. Crear 10 Workspaces (API)

Usar la API REST de AnythingLLM. Crear workspaces **sin cargar documentos** — solo estructura.

### 3.1 Variables de entorno
```powershell
$API = "http://127.0.0.1:3001/api"
$KEY = "TU-API-KEY-AQUI"  # Reemplazar con key real
$HEADERS = @{ "Authorization" = "Bearer $KEY"; "Content-Type" = "application/json" }
```

### 3.2 Workspace definitions

Ejecutar cada bloque por separado. Verificar response `201 Created` o `200 OK`.

#### A1 — Hermes Enterprise
```powershell
$body = @{
    name = "Hermes Enterprise"
    description = "Documentación completa del sistema Hermes Enterprise: SOUL, Capabilities, Operators, Hooks, MCP, Governance, Status Endpoint"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt (post-creación vía UI o PATCH):
```
Eres el asistente documental de Hermes Enterprise. Responde en español con tono técnico-factual.

REGLAS:
1. Cita siempre el ADR de origen (ADR-001 a ADR-006)
2. Distingue DISEÑO (ADR) de IMPLEMENTACIÓN (código)
3. Si una capability/operator existe solo como skeleton, menciónalo
4. OBSERVADO: extraído textualmente de documentos cargados
5. No inferir estado operativo — solo documentación
6. Si la respuesta no está en los documentos cargados, dilo explícitamente

FORMATO: markdown legible en CLI
```

#### A2 — ADRs
```powershell
$body = @{
    name = "ADRs"
    description = "Architectural Decision Records: decisiones pasadas, contexto, alternativas, consecuencias"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el repositorio de ADRs de AI-LAB. Responde en español con tono técnico-factual.

REGLAS:
1. Cita número de ADR y fecha exacta
2. No reinterpretes decisiones — solo resume y referencia
3. Si dos ADRs parecen contradecirse, márcalo explícitamente
4. OBSERVADO: textual de un ADR cargado
5. Si la pregunta no está documentada en ningún ADR, dilo

FORMATO: markdown legible en CLI
```

#### A3 — AI-LAB Runtime
```powershell
$body = @{
    name = "AI-LAB Runtime"
    description = "Documentación del runtime: gateway, router, live-api, SLO, streaming, profiles, prompts, memory"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental de AI-LAB Runtime. Responde en español con tono NOC/operacional.

REGLAS:
1. No inferir estado operativo — cita siempre la fuente documental
2. Distingue DISEÑADO vs IMPLEMENTADO vs PLANEADO
3. Para estado vivo (métricas, endpoints), redirige a Prometheus/Grafana
4. Para preguntas de código, redirige a GitNexus
5. OBSERVADO: extraído textualmente de documentos cargados

FORMATO: markdown legible en CLI
```

#### A4 — Reports
```powershell
$body = @{
    name = "Reports"
    description = "Archivo de reports de fases: qué se hizo, qué se validó, qué falló, qué sigue"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el archivo de reports de fases de AI-LAB. Responde en español.

REGLAS:
1. Cita fase exacta y commit/tag si está disponible
2. Distingue PASS, FAIL, PARTIAL
3. No inferir estado actual de una fase solo por su report
4. OBSERVADO: textual de un report cargado

FORMATO: markdown legible en CLI
```

#### B1 — Rioja Marketplace
```powershell
$body = @{
    name = "Rioja Marketplace"
    description = "Documentación del Marketplace Digital Twin: arquitectura, API, frontend, backend Go, PostgreSQL"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental de Rioja Marketplace. Responde en español.

REGLAS:
1. No confundir Marketplace (Windows Server .150) con AI-LAB runtime (.30)
2. Cita fuente de integración cuando aplique
3. Distingue documentado vs implementado

FORMATO: markdown legible en CLI
```

#### B2 — Observabilidad
```powershell
$body = @{
    name = "Observabilidad"
    description = "Documentación del stack de observabilidad: Prometheus, Grafana, Loki, alertas, dashboards"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental de Observabilidad. Responde en español.

REGLAS:
1. Cita métrica exacta y endpoint Prometheus
2. No inferir estado actual de dashboards — solo documentación de configuración
3. Para estado vivo, redirige a Grafana

FORMATO: markdown legible en CLI
```

#### B3 — Runbooks
```powershell
$body = @{
    name = "Runbooks"
    description = "Procedimientos operativos: reinicio de servicios, recovery, troubleshooting, verificación"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente de Runbooks de AI-LAB. Responde en español.

REGLAS:
1. Si un runbook menciona comandos, listarlos textualmente
2. No modificar procedimientos — solo documentar
3. Advertir si un runbook parece desactualizado
4. Para procedimientos que requieren sudo, marcar que necesitan aprobación

FORMATO: markdown legible en CLI
```

#### C1 — IDS
```powershell
$body = @{
    name = "IDS"
    description = "Documentación del sistema IDS/IPS: syslog, promtail, Loki, dashboards Grafana"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental de IDS/IPS. Responde en español.

REGLAS:
1. No inferir eventos de seguridad activos — solo documentación del pipeline
2. Citar puerto y protocolo exactos
3. Para estado vivo de seguridad, redirige a dashboards dedicados

FORMATO: markdown legible en CLI
```

#### C2 — Stack-2026
```powershell
$body = @{
    name = "Stack-2026"
    description = "Visión global del stack tecnológico: hardware, software, servicios, redes, dominios"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental del Stack-2026. Responde en español.

REGLAS:
1. Citar IPs y servicios exactos de la documentación
2. No inferir disponibilidad — marcar como DOCUMENTADO, no operativo
3. Para estado vivo (qué está UP/DOWN), redirige a operator summary o Grafana

FORMATO: markdown legible en CLI
```

#### C3 — MCP y A2A
```powershell
$body = @{
    name = "MCP y A2A"
    description = "Documentación del ecosistema MCP: servidores, tools, resources, auth, protocolo"
} | ConvertTo-Json
curl.exe -s -X POST "$API/workspace" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

System Prompt:
```
Eres el asistente documental de MCP y A2A. Responde en español.

REGLAS:
1. Distinguir servidores IMPLEMENTADOS vs PLANIFICADOS
2. No documentar tools que no existen en código
3. Si un MCP server está en diseño pero no implementado, marcarlo

FORMATO: markdown legible en CLI
```

---

## 4. Configurar Workspace Parameters (API)

Después de crear cada workspace, configurar chunk/top-K/temperature.

```powershell
# Reemplazar WORKSPACE_ID con el slug/nombre
$ws = "hermes-enterprise"  # o el slug que AnythingLLM asigne
$body = @{
    settings = @{
        similarityThreshold = 0.65
        topN = 5
        chunkSize = 1024
        overlap = 128
        chatSettings = @{
            temperature = 0.2
            maxTokens = 1024
        }
    }
} | ConvertTo-Json -Depth 3

curl.exe -s -X POST "$API/workspace/$ws/update-settings" -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" -d $body
```

Repetir para cada workspace ajustando `similarityThreshold` según la tabla:

| Workspace | similarityThreshold |
|-----------|-------------------:|
| Hermes Enterprise | 0.65 |
| ADRs | 0.70 |
| AI-LAB Runtime | 0.65 |
| Reports | 0.60 |
| Rioja Marketplace | 0.60 |
| Observabilidad | 0.70 |
| Runbooks | 0.70 |
| IDS | 0.65 |
| Stack-2026 | 0.60 |
| MCP y A2A | 0.60 |

---

## 5. Validación Final

### 5.1 Listar workspaces
```powershell
curl.exe -s "http://127.0.0.1:3001/api/workspaces" -H "Authorization: Bearer $KEY"
# → Debe listar 10 workspaces
```

### 5.2 Verificar workspace individual
```powershell
curl.exe -s "http://127.0.0.1:3001/api/workspace/hermes-enterprise" -H "Authorization: Bearer $KEY"
```

### 5.3 Checklist

| # | Item | Comando | Expected |
|---|------|---------|----------|
| 1 | AnythingLLM responde local | `curl 127.0.0.1:3001` | HTML OK |
| 2 | LM Studio responde local | `curl 127.0.0.1:1234/v1/models` | JSON 6 modelos |
| 3 | LLM Provider configurado | UI Settings | LM Studio → qwen2.5-14b |
| 4 | Embeddings configurados | UI Settings | nomic o built-in |
| 5 | Hermes Enterprise creado | API list | workspace presente |
| 6 | ADRs creado | API list | workspace presente |
| 7 | AI-LAB Runtime creado | API list | workspace presente |
| 8 | Reports creado | API list | workspace presente |
| 9 | Rioja Marketplace creado | API list | workspace presente |
| 10 | Observabilidad creado | API list | workspace presente |
| 11 | Runbooks creado | API list | workspace presente |
| 12 | IDS creado | API list | workspace presente |
| 13 | Stack-2026 creado | API list | workspace presente |
| 14 | MCP y A2A creado | API list | workspace presente |
| 15 | System prompts seteados | UI cada workspace | Prompt visible |
| 16 | Chunk/top-K configurado | API update-settings | 1024/128/5 |

### 5.4 Prueba de concepto
```powershell
# Chat test contra un workspace vacío (debe responder con system prompt + "no hay docs")
curl.exe -s -X POST "http://127.0.0.1:3001/api/workspace/hermes-enterprise/chat" `
  -H "Authorization: Bearer $KEY" `
  -H "Content-Type: application/json" `
  -d '{"message":"¿Qué es Hermes Enterprise?"}'
```

---

## 6. Rollback

Si algo falla:
```powershell
# Eliminar workspace
curl.exe -X DELETE "http://127.0.0.1:3001/api/workspace/hermes-enterprise" -H "Authorization: Bearer $KEY"
# Repetir para cada workspace que necesite recreación
```

---

## Notas

- AnythingLLM v13 asigna slugs automáticamente (lowercase, guiones).
- Si no hay API key disponible, crear workspaces manualmente desde la UI:
  ```
  http://127.0.0.1:3001 → Workspaces → "Create Workspace"
  Nombre, descripción, system prompt en la pestaña "Chat Settings".
  ```
- Los chunks de 1024/128 aplican a TODOS los workspaces mientras no se carguen documentos específicos.
- Después de crear los 10 workspaces, reportar resultados aquí y marcamos ANYTHINGLLM-ENTERPRISE-03 como completo.
