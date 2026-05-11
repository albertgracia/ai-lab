# Informe de integración OpenCode + `.agent`

Fecha: 2026-05-11

## Objetivo

Dejar OpenCode conectado a la capa local `.agent` del AI-LAB para que use:

- agentes especializados
- skills por dominio
- reglas globales
- workflows
- memoria semántica
- routing automático de tareas

## Lo que se implementó

### 1) Configuración principal de OpenCode

Archivo: `opencode.json`

Cambios:

- Se configuró el proveedor **LM Studio**.
- Se apuntó al endpoint local `http://localhost:1234/v1`.
- Se registraron modelos locales disponibles.
- Se enlazaron las rutas del ecosistema `.agent`.

Modelos declarados:

- `qwen2.5-coder-14b-instruct`
- `qwen3-14b-claude-sonnet-4.5-reasoning-distill`
- `google/gemma-4-e4b`

### 2) Bootstrap operativo

Archivo: `.agent/BOOTSTRAP.md`

Función:

- Indica a OpenCode cómo usar `.agent` como fuente de verdad.
- Define el orden de prioridad de lectura.
- Explica cómo seleccionar agente, skills y workflows.
- Añade reglas de comportamiento seguras y en español.

### 3) Prompt base de sistema

Archivo: `.agent/OPENCODE_PROMPT.md`

Función:

- Sirve como prompt base para OpenCode en AI-LAB.
- Repite la jerarquía de autoridad.
- Refuerza el uso de `intelligent-routing`.
- Describe el routing automático por dominios.

### 4) Selector automático de agente

Archivo: `.agent/scripts/agent_selector.py`

Función:

- Analiza el texto de la solicitud.
- Sugiere el agente más adecuado.
- Devuelve también skills recomendadas.
- Soporta salida normal y `--json`.

Ejemplo de uso:

```bash
python3 .agent/scripts/agent_selector.py "create an API endpoint for users"
```

Resultado esperado:

- `backend-specialist`

### 5) Documentación de soporte

Archivo: `docs/OPENCODE_AGENT_LAYER.md`

Función:

- Resume cómo funciona la capa OpenCode + `.agent`.
- Enumera archivos clave.
- Incluye ejemplos de uso.
- Explica reglas y modelos disponibles.

## Flujo final de trabajo

1. OpenCode arranca con LM Studio.
2. Se lee `OPENCODE.md`.
3. Se carga `.agent/ARCHITECTURE.md`.
4. Se aplican las reglas de `.agent/rules/GEMINI.md`.
5. Se usa `intelligent-routing` para sugerir agente.
6. Se carga el agente correspondiente.
7. Se cargan solo las skills necesarias.
8. Se responde en español con contexto del AI-LAB.

## Validaciones realizadas

Se comprobó que:

- `opencode.json` es válido.
- El selector Python compila correctamente.
- El selector devuelve una clasificación correcta para una petición API.

Prueba ejecutada:

```bash
python3 .agent/scripts/agent_selector.py "create an API endpoint for users"
```

Salida:

- agente sugerido: `backend-specialist`

## Resultado funcional

El AI-LAB ya tiene una capa operativa para que OpenCode trabaje con su estructura local de agentes, skills, reglas y workflows, sin depender de contexto manual disperso.

## Recomendaciones siguientes

1. Conectar este informe al blog de Astro.
2. Añadir más reglas al selector automático.
3. Crear perfiles de routing por tipo de proyecto.
4. Integrar este flujo con el router cognitivo del laboratorio.
