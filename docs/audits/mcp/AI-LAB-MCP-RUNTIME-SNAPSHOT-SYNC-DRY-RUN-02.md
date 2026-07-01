# AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-DRY-RUN-02

- Resultado: PASS
- HEAD base: `be8ffc30`
- Directorio dry-run temporal: `/tmp/ai-lab-mcp-sync-dry-run-20260606-205826`
- Git sync: `main...origin/main`

## Resumen ejecutivo

Se completo el dry-run de comparacion entre el snapshot versionado `mcp/runtime-mcp/` y el runtime real `/mnt/mcp_server` sin modificar ningun archivo del runtime ni reiniciar servicios.

El diff es entendible y controlable. La futura fase APPLY es **GO** solo si se hace con allowlist explicita de archivos runtime y **NO-GO** para cualquier sync ciego con `--delete`.

## Estado MCP read-only

- `ailab-mcp-semantic-gateway.service`: `active`, `enabled`
- `ailab-mcp-lan-gateway.service`: `active`, `enabled`
- `127.0.0.1:8091`: LISTEN
- `0.0.0.0:8092`: LISTEN

## Tests

Ejecutados:

- `tests/test_mcp_runtime_snapshot_01.py`
- `tests/test_mcp_runtime_metrics_01.py`

Resultado:

- `10 passed`

## Secret scan

Resultado: limpio de secretos reales.

Hallazgos aceptables:

- placeholders/patrones de test
- referencias documentales previas

No se detectaron tokens reales ni secretos reales en la salida auditada.

## Archivos que cambiarian en APPLY

Archivos runtime code modificados respecto a `/mnt/mcp_server`:

- `server.py`
- `lan_server.py`
- `tools/__init__.py`

Archivo nuevo en repo snapshot que se copiaria al runtime:

- `metrics.py`

Archivos iguales entre repo y runtime:

- `config/ailab_semantic_gateway.mcp.json`
- `tools/client.py`
- `tools/incidents.py`
- `tools/latency.py`
- `tools/memory.py`
- `tools/operator.py`
- `tools/route_preview.py`
- `tools/runtime_health.py`
- `tools/slo.py`
- `tools/status.py`

## Repo-only que NO deben copiarse en APPLY

Detectados en el snapshot:

- `README.md`
- `SYNC-POLICY.md`
- directorio vacio `docs/`

Recomendacion:

- no copiar estos elementos al runtime salvo decision explicita posterior
- no usar sync ciego de todo el arbol

## Runtime-only que deben preservarse

Detectados en `/mnt/mcp_server`:

- `logs/`
- `logs/.gitkeep`
- `tools/__pycache__/`
- `__pycache__/`

Interpretacion:

- los caches no son objetivo de sync
- `logs/` debe preservarse
- cualquier APPLY con `--delete` intentaria borrar `logs/`, lo que queda prohibido en esta fase y desaconsejado para la siguiente

## Resultado de rsync --dry-run

### Sin delete

Cambios propuestos observados:

- `>fcst...... lan_server.py`
- `>f+++++++++ metrics.py`
- `>fcst...... server.py`
- `>fcst...... tools/__init__.py`
- adicionalmente intentaria copiar repo-only:
  - `README.md`
  - `SYNC-POLICY.md`
  - `docs/`

### Con delete

Cambios anteriores mas borrados propuestos:

- `*deleting logs/.gitkeep`
- `*deleting logs/`

Conclusion:

- **NO-GO** para `rsync --delete`
- **NO-GO** para sync ciego del directorio completo
- **GO** para APPLY con allowlist exacta y backup previo

## Cambios criticos explicados

### `server.py`

- anade bootstrap de metricas para `8091`
- anade middleware HTTP para requests MCP
- anade ruta `GET /metrics`
- no cambia puerto ni auth

### `lan_server.py`

- anade bootstrap de metricas para `8092`
- anade middleware HTTP para requests MCP
- instrumenta auth success/failure en el middleware ya existente
- anade ruta `GET /metrics`
- no cambia token ni semantica de autenticacion

### `tools/__init__.py`

- reemplaza registro simple por wrapper instrumentado
- cuenta tool calls, errores y duracion sin tocar cada tool por separado

### `metrics.py`

- modulo nuevo de metricas en memoria
- render Prometheus texto
- sin datos sensibles en labels

## Recomendacion GO/NO-GO para APPLY

- Recomendacion global: `GO`, pero solo con estrategia controlada
- Recomendacion para sync ciego con `rsync`: `NO-GO`
- Recomendacion para sync con `--delete`: `NO-GO`

## Estrategia recomendada para APPLY

Preferible usar allowlist exacta de archivos:

- `server.py`
- `lan_server.py`
- `metrics.py`
- `tools/__init__.py`

Y ademas:

- backup previo de `/mnt/mcp_server`
- no copiar `README.md`
- no copiar `SYNC-POLICY.md`
- no crear `docs/` en runtime salvo necesidad real futura
- preservar `logs/`
- excluir `__pycache__` y `.pyc`
- restart controlado de `8091` y `8092` solo en la fase APPLY autorizada

## Confirmaciones de no intervencion

Confirmado en esta fase:

- no se modifico `/mnt/mcp_server`
- no se reinicio ningun servicio
- no se leyo ni mostro token real
- no se toco UFW
- no se tocaron Prometheus ni Grafana
- no se tocaron OpenCode ni LM Studio
- no se toco runtime general
- no se hizo push
- no se creo tag

## Siguiente fase

`AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-APPLY-01`
