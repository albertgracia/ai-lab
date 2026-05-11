# Manual paso a paso: OpenCode + LM Studio en `192.168.1.50`

Fecha: 2026-05-11

## Qué vas a conseguir

Vas a dejar OpenCode conectado a un LM Studio que corre en la IP `192.168.1.50` para poder usar modelos locales desde tu AI-LAB.

## Idea simple

- LM Studio hace de servidor de modelo.
- OpenCode se conecta a ese servidor.
- `.agent` decide qué agente y skills usar.

## Requisitos previos

Antes de empezar, asegúrate de esto:

1. LM Studio está instalado en la máquina `192.168.1.50`.
2. LM Studio tiene un modelo cargado.
3. El servidor local de API de LM Studio está activado.
4. El puerto de la API es el habitual: `1234`.

## Paso 1: Arranca LM Studio

En la máquina `192.168.1.50`:

1. Abre LM Studio.
2. Carga un modelo compatible.
3. Activa el servidor local.
4. Comprueba que escucha en:

```text
http://192.168.1.50:1234/v1
```

## Paso 2: Comprueba que responde

Desde el nodo del AI-LAB, prueba esto:

```bash
curl http://192.168.1.50:1234/v1/models
```

Si devuelve modelos, la conexión básica funciona.

## Paso 3: Configura OpenCode

Abre el archivo `opencode.json` y cambia la URL base.

### Antes

```json
"baseURL": "http://localhost:1234/v1"
```

### Después

```json
"baseURL": "http://192.168.1.50:1234/v1"
```

## Paso 4: Guarda la configuración

El archivo debe seguir apuntando a LM Studio, pero ahora remoto.

Modelo de ejemplo:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "lmstudio": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "LM Studio",
      "options": {
        "baseURL": "http://192.168.1.50:1234/v1"
      },
      "models": {
        "qwen2.5-coder-14b-instruct": {
          "name": "Qwen 2.5 Coder 14B Instruct"
        }
      }
    }
  }
}
```

## Paso 5: Usa OpenCode normalmente

Una vez configurado:

1. Lanza OpenCode.
2. Escribe tu tarea en español.
3. OpenCode leerá `.agent`.
4. El selector elegirá el agente más adecuado.
5. El modelo de LM Studio responderá.

## Paso 6: Qué hace `.agent`

`.agent` no es el modelo. `.agent` es la capa de inteligencia operativa.

Hace tres cosas:

1. Decide qué agente usar.
2. Decide qué skills cargar.
3. Aplica reglas y workflows.

## Paso 7: Cómo saber qué agente se usó

Puedes probar el selector manualmente:

```bash
python3 .agent/scripts/agent_selector.py "create an API endpoint for users"
```

Salida esperada:

- `backend-specialist`

## Paso 8: Si falla

Si no conecta, revisa esto:

1. Que LM Studio esté abierto.
2. Que el modelo esté cargado.
3. Que el puerto `1234` esté activo.
4. Que no haya firewall bloqueando la IP.
5. Que `opencode.json` apunte a `192.168.1.50`.

## Comprobación rápida

```bash
curl http://192.168.1.50:1234/v1/models
python3 .agent/scripts/agent_selector.py --json "build a dashboard card"
```

## Resumen corto

- LM Studio vive en `192.168.1.50`
- OpenCode se conecta por `http://192.168.1.50:1234/v1`
- `.agent` decide el agente y las skills
- el selector automático te ayuda a rutear tareas

## Nota importante

Si más adelante cambias de máquina o puerto, solo tienes que actualizar `baseURL` en `opencode.json`.
