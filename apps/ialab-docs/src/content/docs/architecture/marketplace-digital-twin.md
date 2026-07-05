---
title: "Marketplace Digital Twin"
summary: "Rioja Marketplace como Digital Twin: repositorio indexado en GitNexus, MCP read-only, estado actual de servicios y riesgos conocidos."
order: 9
---

# Marketplace Digital Twin

## ¿Qué es?

Rioja Marketplace es una plataforma e-commerce especializada en productos de la región de La Rioja (España): vinos D.O.Ca. Rioja, aceites de oliva virgen extra y miel artesanal.

El **Digital Twin** no es el sistema productivo. Es un mirror del código fuente con capacidades de consulta vía MCP (read-only) e indexación estructural vía GitNexus. Permite a los agentes de AI-LAB comprender la arquitectura, el estado de servicios y los riesgos del marketplace sin modificar ni desplegar nada.

| Dato | Valor |
|------|-------|
| Código fuente | `/opt/ai-lab-data/marketplace` |
| Remoto | `git@github.com:albertgracia/rioja-marketplace-os` |
| Propósito | Digital Twin observacional, no productivo |
| Acceso MCP | Read-only vía GitNexus + Hermes Marketplace Operator |

---

## GitNexus — Estado de Indexación

El repositorio está indexado en GitNexus con las siguientes características:

| Métrica | Valor |
|---------|-------|
| Nodos | 1,421 |
| Aristas | 2,231 |
| Clusters (comunidades funcionales) | 30 |
| Execution flows | 20 |
| Archivos indexados | 102 |
| Embeddings | ❌ Deshabilitados |

### Limitaciones conocidas

- **Go Fiber routes** (~30 endpoints) **NO detectables** por `route_map`. Las rutas se registran programáticamente en `SetupRoutes()`, no mediante decoradores/anotaciones estáticas. GitNexus no puede mapear handlers → endpoints de forma fiable.
- **Call graph limitado**: los handlers se pasan como referencias de Fiber (`fiber.Handler`), lo que reduce la precisión del grafo de llamadas.
- **Búsqueda híbrida**: BM25 + vector sobre nombres de símbolos. Sin embeddings, la relevancia semántica es menor que en `ai-lab`.

> **Implementado:** indexación completa, 20 execution flows detectados, 30 clusters funcionales.
> **Limitación conocida:** route_map no funcional para Go Fiber programático.

---

## Snapshot de Arquitectura

### Backend — Go + Fiber v2

| Componente | Detalle |
|------------|---------|
| Framework | Go + Fiber v2 |
| Host | `192.168.1.150:8080` |
| Base de datos | PostgreSQL 17 en `localhost:5432/rioja_db` |
| API validada | `GET /api/v1/wines` → `200 OK` (6 productos, 40+ campos) |

### Dominios funcionales

| Dominio | Estado |
|---------|--------|
| Catálogo | ✅ Implementado |
| Inventario | ✅ Implementado |
| ProductMaster | ✅ Implementado |
| Sommelier IA | ✅ Implementado |
| B2B | ✅ Implementado |
| Blog | ✅ Implementado |
| Admin | ⚠️ Auth requerido (antes devolvía 404) |
| Stripe | 🔍 Read-only — integración real pendiente |
| Media | ✅ Implementado |

### Frontend — Next.js

| Componente | Detalle |
|------------|---------|
| Framework | Next.js 15 + React 19 RC |
| Dominio público | `https://marketplace.labrazahome.com` |

---

## Estado MCP

| Componente | Estado | Validación |
|------------|--------|------------|
| GitNexus MCP (read-only) | ✅ Operativo | Acceso a estructura, exec flows, clusters |
| Hermes Marketplace Operator | ✅ Operativo | Consultas vía MCP contract |

Ambos canales son **exclusivamente read-only**. Ninguno permite escritura, despliegue o modificación de infraestructura.

---

## Riesgos Operacionales

### P0 — Críticos

| ID | Riesgo | Impacto |
|----|--------|---------|
| MKT-P0-01 | `CallLMStudio` llama a `getEnv` desde `email_service.go` | **Code smell**: acoplamiento incorrecto entre servicios. `email_service` no debería depender de `CallLMStudio`. |
| MKT-P0-02 | LM Studio URL con fallback a `localhost:1234` | En producción debería apuntar a `192.168.1.250:1234`. El fallback local no es funcional en el servidor real. |
| MKT-P0-03 | Claves de Stripe en `.env` | Secretos en fichero de configuración versionable. Requiere migración a secrets management. |
| MKT-P0-04 | Endpoints Admin requieren autenticación | Comportamiento cambiado: antes devolvían 404 (seguridad por oscuridad), ahora 401/403 explícito. Verificar que el nuevo middleware no introduzca regresiones. |

### P1 — Importantes

| ID | Riesgo | Impacto |
|----|--------|---------|
| MKT-P1-01 | Sin endpoint `/health` en backend Go | No hay forma de validar salud del servicio sin llamar a rutas de negocio. |
| MKT-P1-02 | SmartScan realiza 3 llamadas a `CallLMStudio` por request | Latencia alta en operaciones de escaneado inteligente. `AIChat` suma 1 llamada adicional. |
| MKT-P1-03 | Sin scrape targets Prometheus para marketplace | Cero observabilidad sobre el backend. No hay métricas de latencia, errores ni throughput. |

---

## Necesidades Pendientes

- Acceso físico a `192.168.1.150` para validar secretos y servicios en entorno real
- Integración real de Stripe (actualmente read-only/sandbox)
- Documentación de API de Inventario (pendiente de publicación)
- Mejora general de documentación del marketplace

---

## Separación de Roles

### MCP en Hermes (Digital Twin)

- Acceso **read-only** a la estructura del código vía GitNexus
- Consultas a la API del marketplace vía `Hermes Marketplace Operator`
- Propósito: comprensión arquitectónica, análisis de impacto, depuración
- **No** modifica código, **no** despliega, **no** accede a secretos

### Marketplace Backend (Productivo)

- Sistema real en `192.168.1.150:8080`
- PostgreSQL 17 con datos de producción
- Stripe, emails, escaneado IA — servicios reales
- Requiere acceso físico para mantenimiento

### Reglas

1. El Digital Twin **no es** el sistema productivo. Es mirror de código + API query.
2. Prohibido ejecutar cambios en el backend productivo desde el twin.
3. Prohibido leer claves/secretos del twin (`.env` está en el repositorio pero no debe considerarse fuente de verdad).
4. Prohibido inferir salud del sistema productivo solo desde el código — siempre validar contra el endpoint real.
5. Cualquier intervención en `192.168.1.150` requiere acceso físico validado.

> **Regla operacional:** El Digital Twin informa, no ejecuta. El Marketplace productivo se opera desde consola física sobre `.150`, no desde MCP.

---

## Resumen Operacional

```
Estado:      🟡 OPERATIVO CON RIESGOS
Indexación:  ✅ 1,421 nodos, 30 clusters, 20 execution flows
Backend:     ✅ API validada (GET /api/v1/wines → 200)
Frontend:    ✅ marketplace.labrazahome.com
MCP:         ✅ GitNexus + Hermes Marketplace Operator (read-only)
/health:     ❌ No implementado
Prometheus:  ❌ Sin scrape targets
P0 abiertos: 4 (acoplamiento, URL fallback, secrets, auth)
P1 abiertos: 3 (health, SmartScan latencia, observabilidad)
```

> **Nota:** Este documento es un snapshot del Digital Twin. El estado real del sistema productivo puede diferir. Siempre validar contra `192.168.1.150:8080` antes de conclusions operacionales.
