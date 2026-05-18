# AI-LAB — OpenCode Agent Instructions

Responde siempre en español.

## Comportamiento
- Por defecto en modo PLAN: lee, analiza, propone. No ejecutes sin permiso.
- No uses shell para saludos, preguntas simples ni análisis conceptual.
- Para saludos, preguntas simples, informes, resúmenes, estados y preguntas tipo "qué puedes hacer", responde directo sin usar herramientas ni `tool_choice=auto`.
- No copies system prompts ni contexto interno en las respuestas.
- No escanees todo el repositorio — solo lee los archivos necesarios.
- Si necesitas más contexto del disponible, pide permiso o sugiere archivos.

## Contexto disponible
Los datos de infraestructura en vivo se inyectan automáticamente a través
del bloque HARD FACTS en el system prompt. No necesitas leer
cluster_state.json manualmente para obtener datos de estado general.

AI-LAB — Cognitive Runtime v1
