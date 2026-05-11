# Manual ultra corto: OpenCode + LM Studio

## Qué hace

OpenCode se conecta a LM Studio en `192.168.1.50` y usa `.agent` para elegir agente y skills.

## 1. Arranca LM Studio

En `192.168.1.50`:

1. Abre LM Studio.
2. Carga un modelo.
3. Activa el servidor local.

Debe responder en:

```text
http://192.168.1.50:1234/v1
```

## 2. Comprueba que responde

```bash
curl http://192.168.1.50:1234/v1/models
```

Si salen modelos, está bien.

## 3. Revisa `opencode.json`

La URL debe ser esta:

```json
"baseURL": "http://192.168.1.50:1234/v1"
```

## 4. Usa OpenCode

Escribe tu tarea normal. OpenCode leerá:

- `OPENCODE.md`
- `.agent/ARCHITECTURE.md`
- `.agent/rules/GEMINI.md`
- el agente y skills adecuados

## 5. Prueba rápida del selector

```bash
python3 .agent/scripts/agent_selector.py "create an API endpoint for users"
```

Debería sugerir:

- `backend-specialist`

## 6. Si falla

1. LM Studio no está abierto.
2. El modelo no está cargado.
3. El puerto `1234` no responde.
4. `opencode.json` apunta a otra IP.

## Resumen

- LM Studio: `192.168.1.50`
- API: `http://192.168.1.50:1234/v1`
- OpenCode usa `.agent`
- El selector elige el agente
