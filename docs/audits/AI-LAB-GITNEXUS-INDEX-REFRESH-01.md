# AI-LAB-GITNEXUS-INDEX-REFRESH-01

**Estado:** PARTIAL
**Fecha:** 2026-06-11
**Modo:** operacion controlada de indice GitNexus
**Objetivo:** actualizar el indice GitNexus del repo `ai-lab`, resolver `commitsBehind=44` y verificar su estado operativo sin tocar runtime AI-LAB.

## Resumen ejecutivo

Resultado de la fase:

- el indice GitNexus fue refrescado correctamente contra el checkout local de `/opt/ai-lab` en `.30`
- el `commitsBehind=44` observado en MCP GitNexus quedo resuelto
- GitNexus sigue saludable y el MCP sigue respondiendo
- OpenCode `.50` mantiene conectividad a GitNexus
- **la fase queda PARTIAL** porque el checkout real `/opt/ai-lab` en `.30` sigue **5 commits por detras de `origin/main`**

Conclusion:

- GitNexus ya refleja correctamente el **HEAD local de `.30`**
- GitNexus **todavia no refleja el ultimo `origin/main` publicado**

## 1. Preflight

### Git local de este workspace

- `git status --short` -> limpio
- `HEAD local` -> `10ebf510f55648130caa2184a68ff74a1d48d354`
- `origin/main` local -> `40624c060fa191c2bf19fe2d6b384199ccb9b46c`

### GitNexus health

- `http://gitnexus.ai-lab.local:4747/api/health` -> `{"status":"ok"}`

## 2. Diagnostico inicial

### Estado observado antes del refresh

API `GET /api/repos` y `gitnexus status` en `.30` mostraban:

- `Indexed commit = 8bf3118`
- `Current commit = 80fb61e`
- `Status = stale`
- divergencia indice -> HEAD local: **44 commits**

### Repo real en `.30`

Host: `192.168.1.30`
Path: `/opt/ai-lab`

Medidas observadas:

- `LOCAL_HEAD = 80fb61e195cb67046f48e54ee4457635eaed11e8`
- `ORIGIN_MAIN = 40624c060fa191c2bf19fe2d6b384199ccb9b46c`
- `AHEAD_BEHIND origin/main...HEAD = 5 0`

Interpretacion:

- el checkout `/opt/ai-lab` en `.30` esta **5 commits por detras** de `origin/main`
- el stale `44` era entre **indice GitNexus** y **HEAD local de `/opt/ai-lab`**, no entre GitNexus y el `origin/main` mas reciente

### Commits faltantes en `.30` respecto a `origin/main`

- `40624c06 docs(mcp): document GitNexus MCP config for OpenCode .50`
- `0fb96a0f docs(audit): record 37D runtime smoke partial`
- `60d501c5 runtime(codebase): ground structural health scoring`
- `c838fa7a chore: update public metrics [skip ci]`
- `bc514a96 docs(audit): 37B validation authority recovery report`

## 3. Mecanismo oficial de refresh

Unidad systemd real observada:

- `gitnexus.service`
- `WorkingDirectory=/opt/gitnexus`

Mecanismo soportado por el servicio:

```bash
/usr/local/bin/gitnexus analyze --force --index-only --skip-agents-md --no-stats --max-file-size 32 /opt/ai-lab
```

Se uso tambien validacion previa con CLI `npx gitnexus analyze`, pero la referencia oficial de esta fase es el binario que usa `ExecStartPre` del servicio.

## 4. Refresh ejecutado

### Paso 1: refresh seguro del indice

Comando ejecutado en `.30`:

```bash
/usr/local/bin/gitnexus analyze --force --index-only --skip-agents-md --no-stats --max-file-size 32 /opt/ai-lab
```

Resultado:

- `returncode = 0`
- `duration_sec = 18.95`
- `Repository indexed successfully (18.0s)`

Evidencia reportada por CLI:

- `19.692 nodes`
- `29.201 edges`
- `461 clusters`
- `300 flows`

Notas:

- sin borrado manual del indice
- sin reinicio de GitNexus
- sin reinicio de servicios AI-LAB

## 5. Validacion post-refresh

### Salud del servicio

- `GET /api/health` -> `ok`
- MCP GitNexus sigue operativo

### API / MCP

`GET /api/repos` via hostname LAN:

- repo `ai-lab` visible
- `lastCommit = 80fb61e...`
- sin campo `staleness` en la salida observada post-refresh

Interpretacion:

- el stale de `44` queda resuelto respecto al checkout local de `.30`

### MCP smoke read-only

#### `list_repos`

- PASS
- repo `ai-lab` visible
- path `/opt/ai-lab`

#### `query("ai-lab")`

- PASS
- GitNexus devuelve resultados reales del repo

#### `context(runtime/codebase/gitnexus_memory.py::_compute_score)`

- PASS
- simbolo encontrado
- callers detectados correctamente:
  - `test_compute_score_returns_dict`
  - `test_compute_score_deterministic`
  - `load_codebase_memory`

### OpenCode `.50`

Conectividad observada post-refresh:

- conexion TCP establecida desde `.50` hacia `192.168.1.30:4747`

Interpretacion:

- OpenCode `.50` sigue conectado a GitNexus tras el refresh

## 6. Hallazgo principal

### Resuelto

- `commitsBehind=44` del indice GitNexus respecto al `HEAD` local de `/opt/ai-lab`

### No resuelto en esta fase

- `/opt/ai-lab` en `.30` sigue 5 commits por detras de `origin/main`

Consecuencia:

- GitNexus ya no esta stale respecto al checkout local
- pero **todavia no puede considerarse reflejo exacto del ultimo `origin/main`** mientras `.30` no sincronice su checkout

## 7. Runtime safety

Confirmado:

- no se toco Gateway
- no se toco Router
- no se toco Prometheus
- no se toco Qdrant/Postgres
- no se tocaron modelos ni LM Studio
- no se reinicio ningun servicio AI-LAB
- no hubo acciones destructivas
- no se expusieron secretos

## 8. Veredicto

**PARTIAL**

Justificacion:

1. el indice GitNexus fue refrescado correctamente
2. el stale `44` quedo resuelto frente al `HEAD` local de `.30`
3. GitNexus health y MCP quedaron operativos
4. OpenCode `.50` sigue conectando
5. `/opt/ai-lab` en `.30` sigue 5 commits por detras de `origin/main`, asi que el objetivo de reflejar el ultimo `main` publicado no queda completamente cerrado

## 9. Siguiente fase propuesta

**AI-LAB-GITNEXUS-ORIGIN-ALIGNMENT-01**

Objetivo:

- alinear el checkout real `/opt/ai-lab` de `.30` con `origin/main` de forma controlada
- reejecutar `gitnexus analyze`
- confirmar que GitNexus refleja el commit `40624c06...` o el `origin/main` vigente en ese momento
