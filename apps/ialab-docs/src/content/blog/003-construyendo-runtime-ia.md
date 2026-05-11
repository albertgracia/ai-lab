---
title: "Construyendo un runtime IA distribuido"
date: "2026-05-10"
summary: "Cómo AI-LAB terminó usando GPUs remotas, routing OpenAI-compatible y observabilidad."
tags: ["runtime", "gpu", "router"]
---

Uno de los problemas más interesantes de AI-LAB apareció muy pronto:

¿Cómo usar varios nodos GPU como una única plataforma?

La solución terminó convirtiéndose en un pequeño runtime distribuido.

## El problema inicial

Al principio cada LM Studio era independiente.

Cada nodo tenía su IP, sus modelos, sus puertos y su estado.

Eso obligaba a cambiar endpoints manualmente, recordar nodos y gestionar caídas.

No era operativo.

## La solución

Se creó un Router API compatible con OpenAI.

```text
/v1/chat/completions
