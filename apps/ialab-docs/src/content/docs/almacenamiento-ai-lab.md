---
title: "Almacenamiento AI-LAB"
summary: "Arquitectura de almacenamiento persistente del laboratorio."
order: 10
---

El AI-LAB utiliza una arquitectura de almacenamiento separada por función.

## Capas principales

| Ruta | Uso |
|---|---|
| `/` | Sistema operativo y runtime base |
| `/mnt/ai-models` | Modelos IA, pesos, checkpoints y caché de modelos |
| `/opt/ai-lab` | Código, configuración y servicios del laboratorio |
| `/opt/ai-lab-data` | Datos persistentes del laboratorio |

## Volumen dedicado

Se ha creado un volumen LVM dedicado:

```text
/opt/ai-lab-data
