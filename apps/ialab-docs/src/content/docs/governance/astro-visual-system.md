---
title: AI-LAB Astro Visual System
summary: Estándar visual y checklist de publicación para páginas Astro de AI-LAB.
---

# AI-LAB Astro Visual System

## Propósito

Este documento fija el estándar visual para futuras páginas y actualizaciones Astro. La meta es mantener una presentación premium, técnica y coherente entre /infra, /ai-infrastructure, observabilidad, status, runbooks y páginas futuras.

## Principios visuales

- Oscuro premium.
- Acentos cyan/teal.
- Jerarquía ejecutiva primero.
- Contenido técnico después.
- Evitar tablas crudas cuando una matriz o card sea más legible.
- Separar resultado técnico PASS de resultado visual PASS.
- Mantener coherencia entre páginas internas y documentación operativa.

## Anatomía estándar de página

- Hero / encabezado.
- Estado operativo.
- Executive summary cards.
- Secciones principales.
- Matrices operativas.
- Roadmap.
- Riesgos residuales.
- Próxima fase.

## Patrones documentales estándar

Estos nombres describen patrones visuales/documentales. No implican que exista todavía un componente Astro con ese nombre.

- HeroBlock.
- StatusCard.
- MetricCard.
- OperationalMatrix.
- RoadmapPanel.
- ToolMatrix.
- CalloutSuccess.
- CalloutWarning.
- CalloutCritical.
- OperatorAction.
- SecurityNote.

## Badges estándar

- confirmed.
- active.
- standby.
- pending.
- reserved.
- low risk.
- medium risk.
- critical.
- operator action.
- read-only.
- mutable.
- destructive.

## Roadmap estándar

- Completado recientemente.
- Próximo bloque.
- Pendiente.
- En reserva.
- Operator action.
- No convertir Roadmap en changelog largo.

## MCP Tools estándar

- Tools confirmadas.
- Uso activo.
- En preparación.
- En reserva.
- Condiciones de activación.
- AILAB_MCP_TOKEN como nombre de variable, sin valor real.
- LAN controlled mode.
- Read-only por defecto.
- Acciones mutables o destructivas en reserva salvo aprobación.

## Tablas y matrices

- Tabla solo si mejora lectura.
- Máximo 5 columnas cuando sea posible.
- Para tools y roadmap, preferir cards o matriz visual.
- Evitar contenido plano sin jerarquía.

## Seguridad y sanitización

- No tokens.
- No credenciales.
- No endpoints sensibles.
- No seriales.
- No identificadores GPON completos.
- IPs internas solo si la página es interna o protegida y hay justificación.
- En caso de duda, usar versión sanitizada.

## Checklist de publicación Astro

Antes de commit:

- npm run build PASS.
- Ruta validada en dist.
- Sin secretos.
- Sin tokens reales.
- Sin seriales.
- Sin IPs sensibles salvo justificación.
- Diseño revisado.
- No tablas crudas innecesarias.
- Roadmap actualizado si aplica.
- MCP Tools actualizadas si aplica.
- Informe de auditoría creado.
- No runtime ni servicios tocados.
- Visual review antes de push.

## Aplicación obligatoria

Futuras fases Astro deben:

- Reutilizar estos patrones.
- Evitar HTML/CSS ad hoc sin justificación.
- Incluir revisión visual antes de push.
- Separar contenido técnico de aceptación visual.

## Próxima aplicación

- Próxima fase recomendada: AI-LAB-ASTRO-ROADMAP-MCP-TOOLS-VISUAL-APPLY-01
- Objetivo: aplicar este estándar a /ai-infrastructure.
