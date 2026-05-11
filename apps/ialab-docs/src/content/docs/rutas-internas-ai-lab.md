---
title: "Rutas internas AI-LAB"
summary: "URLs principales del laboratorio y servicios internos."
order: 4
---

Listado de accesos principales del laboratorio.

## Accesos principales

| Servicio | URL | Función |
|---|---|---|
| AI-LAB Docs | `http://192.168.1.30:4321` | Portal documental |
| Dashboard vivo | `http://192.168.1.30:4321/status` | Estado operativo |
| Servicios | `http://192.168.1.30:4321/services` | Accesos internos |
| OpenCode | `http://192.168.1.30:4096` | Interfaz agentic |
| Open WebUI | `http://192.168.1.30:3000` | Frontend IA |
| Portainer | `http://192.168.1.30:9000` | Gestión Docker |
| Qdrant | `http://192.168.1.30:6333` | Base vectorial |
| Router API | `http://192.168.1.30:8008` | API OpenAI-compatible |

## Endpoints Router API

| Endpoint | Uso |
|---|---|
| `/` | Información del servicio |
| `/health` | Healthcheck |
| `/v1/models` | Modelos disponibles |
| `/v1/chat/completions` | Chat completions |

## Credenciales conocidas

| Servicio | Usuario | Contraseña |
|---|---|---|
| OpenCode | `opencode` | `ailab` |
| Open WebUI | pendiente documentar | pendiente documentar |
| Portainer | pendiente documentar | pendiente documentar |

## Validación rápida

```bash
curl http://192.168.1.30:8008/health
curl http://192.168.1.30:8008/v1/models
curl -I http://192.168.1.30:4321
