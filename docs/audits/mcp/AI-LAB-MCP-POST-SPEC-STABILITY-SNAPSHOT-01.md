# AI-LAB-MCP-POST-SPEC-STABILITY-SNAPSHOT-01

- Resultado: PARTIAL
- Fecha/hora auditoria: 2026-06-06 20:30 CEST aprox.
- Host auditado: `ubuntu-ialab` (`192.168.1.30` presente en `hostname -I`)
- Workspace auditado: `/opt/ai-lab`
- Usuario: `albert`
- Rama: `main`
- HEAD inicial: `ecb9bd68`
- HEAD final pre-commit: `ecb9bd68`
- Git sync: `main...origin/main` sin commits locales ni remotos pendientes tras `git fetch origin`

## Resumen ejecutivo

El repositorio y los servicios MCP auditados permanecen estables en modo read-only. No se detectaron cambios inesperados en el working tree, los dos servicios MCP estan `active` y `enabled`, los puertos esperados escuchan correctamente, el test snapshot pasa `5/5`, el secret scan no mostro secretos reales y la documentacion clave sigue presente.

La auditoria queda en `PARTIAL` por una unica razon: la comprobacion de UFW mediante `sudo -n ufw status verbose` no estuvo disponible sin autenticacion interactiva, por lo que ese punto no pudo verificarse sin romper la restriccion de la fase.

## Preflight y Git

- `hostname`: `ubuntu-ialab`
- `pwd`: `/opt/ai-lab`
- `git rev-parse --show-toplevel`: `/opt/ai-lab`
- `whoami`: `albert`
- `git status --short` inicial: limpio
- `git status -sb` inicial: `## main...origin/main`
- `git branch --show-current`: `main`
- `git rev-parse --short HEAD`: `ecb9bd68`
- `git fetch origin`: OK
- `git log origin/main..HEAD`: vacio
- `git log HEAD..origin/main`: vacio

## Servicios MCP

### `ailab-mcp-semantic-gateway.service`

- Estado: `active (running)`
- Enabled: `enabled`
- MainPID: `1510`
- Bind observado: `127.0.0.1:8091`
- Comando observado: `/opt/ai-lab/.venv/bin/python /mnt/mcp_server/server.py`
- Uptime en el momento de la auditoria: ~9h

### `ailab-mcp-lan-gateway.service`

- Estado: `active (running)`
- Enabled: `enabled`
- MainPID: `1498`
- Bind observado: `0.0.0.0:8092`
- Comando observado: `/opt/ai-lab/.venv/bin/python /mnt/mcp_server/lan_server.py`
- Uptime en el momento de la auditoria: ~9h

## Puertos

Salida relevante de `ss -ltnp`:

- `127.0.0.1:8091` LISTEN -> proceso `python` PID `1510`
- `0.0.0.0:8092` LISTEN -> proceso `python` PID `1498`

Resultado: PASS

## UFW

Comando ejecutado:

```bash
sudo -n ufw status verbose
```

Resultado observado:

```text
sudo: interactive authentication is required
```

Interpretacion:

- No se pudo verificar el estado de UFW sin autenticacion interactiva.
- No se solicito password.
- No se realizo ninguna accion sobre firewall.

Resultado: PARTIAL

## Endpoints basicos

### Puerto 8091

- `GET http://127.0.0.1:8091/health` -> `404 Not Found`
- `GET http://127.0.0.1:8091/mcp` -> `406 Not Acceptable`
- Payload observado en `/mcp`: el servicio exige cliente con `Accept: text/event-stream`

Interpretacion:

- El servicio responde y el endpoint MCP esta vivo.
- `/health` no esta expuesto en este gateway; no se considera cambio operativo durante esta fase.

### Puerto 8092 sin token

- `GET http://127.0.0.1:8092/mcp` -> `401 Unauthorized`

Resultado:

- Comportamiento esperado confirmado sin leer ni usar token.

## Logs recientes

### Semantic gateway

- No se observaron tracebacks recientes.
- No se observo crashloop activo.
- Se observaron reinicios historicos alineados con boots previos, no repetitivos en ventana corta.
- En la ventana actual solo aparecen accesos de comprobacion y respuestas `404/406` coherentes con las pruebas read-only.

### LAN gateway

- No se observaron tracebacks recientes.
- No se observo crashloop.
- Se observan secuencias normales `POST /mcp 200`, `POST /mcp 202`, `GET /mcp 200` desde `192.168.1.50`.
- Se registro `401 Unauthorized` en el chequeo sin token, comportamiento esperado.

Resultado logs: PASS

## Tests snapshot

Comando:

```bash
./.venv/bin/python -m pytest -q tests/test_mcp_runtime_snapshot_01.py
```

Resultado:

```text
5 passed in 0.02s
```

Resultado tests: PASS

## Secret scan

Paths auditados:

- `docs/mcp`
- `docs/audits`
- `mcp/runtime-mcp`
- `tests/test_mcp_runtime_snapshot_01.py`

Hallazgos observados:

- coincidencia documental en `docs/audits/AI-LAB-ASTRO-DOCS-CONSOLIDATION-FINAL-01.md` describiendo patrones de busqueda
- placeholders/patrones de prueba en `tests/test_mcp_runtime_snapshot_01.py` (`BEGIN RSA`, `BEGIN OPENSSH`, `private_key`, `PASSWORD=`, `SECRET=`, `API_KEY=`)

Evaluacion:

- No se mostro token real
- No se detectaron secretos reales en la salida revisada

Resultado secret scan: PASS

## Documentacion clave

Archivos presentes:

- `docs/mcp/AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md`
- `docs/mcp/AI-LAB-MCP-TOOLS-CATALOG-FINAL-01.md`
- `docs/mcp/AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-01.md`
- `docs/mcp/AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01.md`

Conteo lineas:

- `AI-LAB-MCP-CLIENT-CONFIG-DOCS-01.md`: 260
- `AI-LAB-MCP-TOOLS-CATALOG-FINAL-01.md`: 178
- `AI-LAB-MCP-TOOLS-RESOURCES-PROMPTS-SPEC-01.md`: 422
- `AI-LAB-MCP-OBSERVABILITY-METRICS-SPEC-01.md`: 505

Resultado documentacion: PASS

## Confirmaciones de no intervencion

Confirmado durante esta fase:

- no se reinicio ningun servicio
- no se modifico ninguna configuracion operativa
- no se leyo ni mostro ningun token
- no se modifico `/mnt/mcp_server`
- no se modifico `mcp/runtime-mcp`
- no se toco `/etc/ai-lab/mcp-lan.env`
- no se tocaron Prometheus ni Grafana
- no se tocaron OpenCode ni LM Studio
- no se toco runtime ni `runtime/state`
- no se tocaron Gateway ni Router
- no se hizo push
- no se creo tag

## Clasificacion final

- Resultado global: PARTIAL
- Motivo del parcial: comprobacion UFW no verificable con `sudo -n` sin autenticacion interactiva
- Riesgo operativo actual observado: bajo
- Estabilidad MCP observada: estable

## Siguiente fase recomendada

Como la unica desviacion es documental/de verificacion y no funcional, la siguiente fase recomendada sigue siendo:

`AI-LAB-MCP-OBSERVABILITY-METRICS-IMPLEMENTATION-01`

Nota: antes de ejecutarla, conviene decidir si la verificacion de UFW debe aceptarse como `NO DISPONIBLE` en read-only o si se quiere una ventana controlada con permisos no interactivos para cerrarla como PASS.
