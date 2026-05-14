---
title: AI-LAB OpenAI Gateway Stable
summary: Integración estable entre OpenCode, AI-LAB Gateway y LM Studio
status: stable
category: gateway
pubDate: 2026-05-14
tags:
  - ai-lab
  - gateway
  - lmstudio
  - opencode
  - distributed-ai
---

# AI-LAB OpenAI Gateway Stable

## Objetivo

Crear una capa middleware entre OpenCode y LM Studio para:

- sanitización de reasoning
- routing cognitivo
- gobernanza
- inyección de contexto
- compatibilidad OpenAI API

---

# Arquitectura

OpenCode → AI-LAB Gateway → LM Studio → Modelos

## Backend

- LM Studio
- OpenAI-compatible API
- DeepSeek R1 Distill Qwen 14B
- Qwen reasoning models

## Gateway

Puerto:

```bash
8008
