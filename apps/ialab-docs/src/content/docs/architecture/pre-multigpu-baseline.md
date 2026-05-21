---
title: "Pre-Multi-GPU Baseline"
summary: "Baseline oficial del runtime antes de reactivar Multi-GPU: un solo backend activo, un backend inventariado y contrato semántico de sensores estabilizado."
order: 19
---

## Baseline

- RX9070 activa
- RX7900XT inventariada / expected_offline
- sensor semantics normalizadas
- evidence-bound reporting operativo
- storage archive governance activo

## Diagrama

```mermaid
flowchart LR
    A[RX9070 active]
    I[RX7900XT expected_offline]
    S[sensor semantics]
    G[governance]
    F[future scheduler]

    A --> S
    I --> S
    S --> G
    G -.baseline.-> F
```

## Qué significa

El runtime ya sabe distinguir:

- activo vs inventariado
- observado vs derivado
- fresh vs unavailable
- confidence crítica vs no crítica

Eso es el prerequisito para cualquier scheduler serio.
