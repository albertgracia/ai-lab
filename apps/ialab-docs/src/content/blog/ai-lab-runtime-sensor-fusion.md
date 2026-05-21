---
title: "AI-LAB Runtime Sensor Fusion: de métricas a contexto operacional"
description: "Cómo AI-LAB dejó de tratar Prometheus como un dashboard pasivo y lo convirtió en evidencia operativa para el LLM."
summary: "FASE 30I transformó métricas aisladas en contexto operacional usable por el runtime: sensor fusion, topología, confidence per-domain y summaries GPU compactos."
date: "2026-05-21"
tags:
  - ai-lab
  - runtime
  - sensor-fusion
  - observability
  - prometheus
---

# AI-LAB Runtime Sensor Fusion: de métricas a contexto operacional

Prometheus suele acabar en el mismo sitio: dashboards, alertas y poco más. En AI-LAB, 30I cambia esa relación. Las métricas dejan de ser solo telemetría y pasan a formar parte del contexto operativo del runtime.

El salto no fue estético. Fue epistemológico. El LLM ya no recibe una descripción verbal del estado del sistema. Recibe un contrato respaldado por sensores: topología, nodos GPU, modelos activos, confianza por dominio y semántica `expected_offline`.

## Qué cambió exactamente

Antes, el runtime sabía enrutar. Después de 30I, también sabe observarse.

Eso significa:

- distinguir inventario de runtime activo
- derivar topología desde sensores
- evitar que una GPU inventariada aparezca como activa
- responder preguntas GPU con métricas vivas

## RX9070 y RX7900XT: el caso que define la fase

RX9070 está activa. RX7900XT está inventariada y apagada. El runtime ya no trata ambos nodos como equivalentes. Esa diferencia es la base real de cualquier evolución posterior hacia Multi-GPU.

## La lección

Si el runtime no puede describirse a sí mismo con precisión, no está listo para escalar. Sensor fusion no fue un lujo. Fue el baseline necesario.
