---
title: "Storage Archive Policy"
summary: "Política operativa de archive histórico: separación entre runtime vivo, runtime data, modelos y NAS; manifests, exclusiones y detección anti-recursiva."
order: 18
---

## Objetivo

Evitar que el runtime activo acumule backups, snapshots recursivos, burn-ins y artifacts históricos dentro del disco principal.

## Tiers

- `/opt/ai-lab` -> runtime vivo
- `/opt/ai-lab-data` -> runtime data
- `/mnt/ai-models` -> modelos
- `/mnt/opencode/ai-lab-archives` -> archives históricos

## Reglas

- Todo backup usa `.backup-excludes`
- `/opt/ai-lab/backups` queda deprecated
- archives completos solo en NAS
- detección de recursividad **before copy**
- todo archive genera manifest JSON

## Flujo

```mermaid
flowchart LR
    R[/opt/ai-lab]
    A[archive_manager.py]
    E[.backup-excludes]
    N[/mnt/opencode/ai-lab-archives]
    M[manifest.json]

    R --> A
    E --> A
    A --> N
    A --> M
```

## Riesgo resuelto

El problema principal detectado no era `backups/` sino `snapshots/` recursivos que contenían `backups/` dentro de árboles archivables.
