---
title: "FASE 16 - Observe Mode and Readonly Shell"
summary: "Runbook para activar observe, validar analisis ligero y probar comandos readonly seguros."
status: stable
category: milestone
date: "2026-05-17"
---

# FASE 16

## Objetivo

Permitir analisis tecnico/operativo sin `HARD_FACTS` obligatorio y con shell readonly segura.

## Validaciones

1. Cambiar a `observe` con `/api/mode/switch?mode=observe`.
2. Probar `hola` y verificar respuesta breve.
3. Probar analisis operativo y verificar salida natural, no estructurada.
4. Ejecutar `pwd` o `ls /opt/ai-lab` y verificar que se permiten.
5. Ejecutar `reboot` y verificar bloqueo.

## Resultado esperado

- respuestas breves y observables
- sin `HARD_FACTS` obligatorio
- shell readonly permitida
- comandos peligrosos bloqueados
- contexto observable mínimo para informes técnicos
