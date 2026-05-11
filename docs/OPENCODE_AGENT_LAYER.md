# OpenCode + .agent en AI-LAB

## Qué hace esta integración

OpenCode usa LM Studio como modelo local y carga el árbol `.agent` como capa operativa:

- agentes especializados
- skills por dominio
- reglas globales
- workflows
- memoria semántica

## Archivos clave

- `opencode.json`: configuración del modelo y rutas del contexto
- `.agent/BOOTSTRAP.md`: instrucciones de arranque para OpenCode
- `.agent/OPENCODE_PROMPT.md`: prompt base del sistema
- `.agent/scripts/agent_selector.py`: selector automático de agente

## Cómo funciona

1. OpenCode arranca con LM Studio.
2. Se lee `OPENCODE.md` y luego `.agent/ARCHITECTURE.md`.
3. El selector decide qué agente encaja mejor.
4. Se cargan las skills mínimas necesarias.
5. Se responde aplicando el rol especializado.

## Uso rápido

### Ver sugerencia de agente

```bash
python .agent/scripts/agent_selector.py "create an API endpoint for users"
```

### Ver salida en JSON

```bash
python .agent/scripts/agent_selector.py --json "build a dashboard card"
```

### Modelos disponibles en LM Studio

- `qwen2.5-coder-14b-instruct`
- `qwen3-14b-claude-sonnet-4.5-reasoning-distill`
- `google/gemma-4-e4b`

## Reglas importantes

- No inventar rutas, puertos o servicios.
- Si la petición es ambigua, preguntar antes de codificar.
- Si hay varios dominios, usar `orchestrator`.
- Responder siempre en español.
