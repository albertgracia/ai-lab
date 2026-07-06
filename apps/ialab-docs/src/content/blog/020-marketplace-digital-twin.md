---
title: "Marketplace Digital Twin: observabilidad estructural de un ecosistema real"
date: "2026-07-03"
summary: "El Rioja Marketplace se replica como Digital Twin observacional en AI-LAB: indexado en GitNexus, accesible vía MCP read-only y documentado para análisis estructural."
tags:
  - ai-lab
  - marketplace
  - digital-twin
  - gitnexus
  - mcp
---

## ¿Qué es el Marketplace Digital Twin?

El Rioja Marketplace es una aplicación real (Go + Fiber v2, Next.js 15, PostgreSQL 17) que opera en la red privada. AI-LAB lo replicó como Digital Twin observacional — no para modificarlo, sino para observarlo, entenderlo y correlacionarlo con el resto del ecosistema.

## Componentes

| Componente | Tecnología | Rol |
|------------|-----------|-----|
| Backend | Go + Fiber v2 | API REST, autenticación, pagos |
| Frontend | Next.js 15 + React 19 RC | Interfaz de usuario |
| Base de datos | PostgreSQL 17 | Persistencia |
| Indexación | GitNexus (1421 nodos, 2231 aristas) | Cognición estructural |
| MCP | Hermes Marketplace Operator | Acceso read-only |

## Integración con GitNexus

El repositorio del marketplace está indexado en GitNexus con 1421 nodos y 2231 relaciones. Esto permite:

- **Impact analysis**: saber qué cambia si se modifica un handler
- **Context queries**: entender flujos completos (auth → carrito → pago)
- **Route mapping**: ver qué endpoints consumen qué componentes
- **Process tracing**: seguir execution flows desde la petición hasta la base de datos

## MCP read-only

El Hermes Marketplace Operator expone acceso read-only al marketplace vía MCP. Esto permite al runtime de AI-LAB consultar el estado del marketplace sin intervenir en su operación.

## Estado actual

- Indexación GitNexus: completa
- MCP read-only: validado y operativo
- Backend: Go + Fiber v2 en red privada, PostgreSQL 17
- Frontend: Next.js 15 + React 19 RC
- URL pública: marketplace.labrazahome.com
- Stripe: en sandbox (pendiente de activación real)

Documentación en [docs/architecture/marketplace-digital-twin/](/docs/architecture/marketplace-digital-twin/).
