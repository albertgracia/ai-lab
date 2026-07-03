# AI-LAB-RUNTIME-GROUNDING-UNKNOWN-STATE-TOKENS-FIX-01

## Resultado: PARTIAL

Fix aplicado en repo y validado por import/py_compile/tests, pero el runtime vivo sigue ejecutando el proceso anterior porque no se permite reiniciar gateway en esta fase. El bug de codigo queda corregido; la verificacion live del endpoint aun refleja el binario viejo.

---

## 1) Estado Git inicial

- Repo: `/opt/ai-lab`
- Branch: `main`
- HEAD base: `1eab3ba1`
- Estado inicial: working tree limpio salvo el informe NOC previo (ya commiteado)
- Branch tracking: `main...origin/main [ahead 1]`

---

## 2) Referencias encontradas

### Uso directo

- `runtime/gateway/openai_gateway.py:2021`
  - `"unknown_state_semantics": sorted(UNKNOWN_STATE_TOKENS)`

### Fuente canónica

- `runtime/context/runtime_grounding.py:22-28`
  - `UNKNOWN_STATE_TOKENS = frozenset({...})`

### Tests relacionados

- `tests/test_runtime_grounding_30ig.py:6`
  - importa `UNKNOWN_STATE_TOKENS`
- `tests/test_runtime_grounding_30ig.py:268`
  - valida que `unknown_state` pertenezca a `UNKNOWN_STATE_TOKENS`

---

## 3) Causa raiz

`openai_gateway.py` usaba `UNKNOWN_STATE_TOKENS` en la ruta `/runtime/grounding`, pero no lo importaba desde `runtime.context.runtime_grounding`.

Eso provocaba:

- `NameError: UNKNOWN_STATE_TOKENS is not defined`
- endpoint `/runtime/grounding` en estado `degraded`

---

## 4) Fix aplicado

### Archivo modificado

- `runtime/gateway/openai_gateway.py`

### Cambio minimo

Se agregó el import canónico:

```python
from runtime.context.runtime_grounding import (
    is_runtime_grounded_prompt,
    validate_response_against_observed_runtime,
    build_grounding_envelope,
    UNKNOWN_STATE_TOKENS,
)
```

### Ajuste de test

- `tests/test_runtime_grounding_30ig.py`
  - se corrigió la expectativa de `contract_version` de `30I-G` a `31E`, alineada con el contrato real actual de `build_grounding_envelope()`.

No se alteró la lógica de grounding.

---

## 5) Validaciones de codigo

### py_compile

PASS:

- `python3 -m py_compile runtime/context/runtime_grounding.py runtime/gateway/openai_gateway.py tests/test_runtime_grounding_30ig.py`

### Import check

PASS:

- `import runtime.gateway.openai_gateway as g`
- `hasattr(g, 'UNKNOWN_STATE_TOKENS') == True`

---

## 6) Tests

### Grounding

PASS:

- `PYTHONPATH=/opt/ai-lab pytest -q tests/test_runtime_grounding_30ig.py`
- Resultado: `36 passed`

### Operational reporting

PASS:

- `PYTHONPATH=/opt/ai-lab pytest -q tests/test_operational_reporting_31c.py`
- Resultado: `21 passed, 1 warning`

### Nota

El primer intento de pytest sin `PYTHONPATH` fallo por import path del entorno, no por el fix.

---

## 7) Revalidacion runtime read-only

### Endpoints

- `GET /runtime/grounding` en gateway vivo: sigue devolviendo
  - `status: degraded`
  - `error: name 'UNKNOWN_STATE_TOKENS' is not defined`

### Interpretacion

Esto confirma que el proceso `ailab-gateway.service` sigue cargando el codigo anterior. No se reinicio el gateway por regla de fase, asi que el fix aun no puede reflejarse en el runtime vivo.

### Otros endpoints

- `GET /runtime/health/summary` en gateway: devuelve estado critico, sin cambio de base
- `GET /runtime/health/summary` en router: `404`
- `GET /runtime/health/summary` en live-api: `404`

---

## 8) Logs limitados

- `journalctl -u ailab-router.service`: sin rastro de `UNKNOWN_STATE_TOKENS`/`NameError`/`grounding`
- `journalctl -u ailab-gateway.service`: sin rastro nuevo visible en la ultima ventana consultada

### Nota

La ausencia de nuevos logs no contradice el endpoint vivo: el servicio sigue corriendo el proceso viejo y no se reinicio.

---

## 9) Estado NOC/runtime tras fix

### Repo

- Bug corregido en codigo.
- Tests relevantes pasan.

### Runtime vivo

- `runtime/grounding` sigue degradado porque el proceso en memoria no fue reiniciado.
- SLO / runtime critico sigue explicado por inferencia apagada + runtime viejo cargado.

---

## 10) Riesgos residuales

1. El gateway vivo sigue ejecutando el binario viejo hasta el siguiente restart permitido.
2. El backend de inferencia sigue apagado de forma operativa esperada.
3. El runtime critico sigue presente por la capa cognitiva, no por una caida de infraestructura.
4. `runtime/grounding` requiere reinicio futuro del gateway para hacer efectivo el fix en vivo.

---

## 11) Que no se hizo

- No se arranco backend de inferencia.
- No se arranco LM Studio/Ollama/model server.
- No se reinicio Gateway.
- No se reinicio Router.
- No se reinicio Live API.
- No se reinicio GitNexus.
- No se reinicio Qdrant.
- No se reinicio Prometheus.
- No se reinicio Grafana.
- No se toco Docker.
- No se toco systemd.
- No se toco configuracion.
- No se hizo push.
- No se creo tag.

---

## 12) Siguiente fase recomendada

Cuando se permita un restart controlado del gateway, validar de nuevo `GET /runtime/grounding` para confirmar que el `NameError` desaparecio y que el contract `unknown_state_semantics` queda expuesto correctamente.

*Fin del informe - 31/05/2026*
