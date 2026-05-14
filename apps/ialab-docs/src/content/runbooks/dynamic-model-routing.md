---
title: "Dynamic Capability-Aware Model Routing"
summary: "AI-LAB implementa selección dinámica de modelos basada en capacidades descubiertas automáticamente desde LM Studio."
status: "stable"
category: "distributed-runtime"
tags:
  - routing
  - lmstudio
  - orchestration
  - inference
  - distributed-ai
  - token-routing
date: "2026-05-14"
---

# Dynamic Capability-Aware Model Routing

## Objetivo

Eliminar dependencias hardcoded de modelos concretos y permitir que AI-LAB:

- descubra modelos dinámicamente
- infiera capacidades automáticamente
- seleccione modelos óptimos según tarea
- adapte el runtime al estado real del cluster

---

# Arquitectura

## Antes

```text
Router
→ modelo fijo
→ contexto fijo
→ capacidades manuales
