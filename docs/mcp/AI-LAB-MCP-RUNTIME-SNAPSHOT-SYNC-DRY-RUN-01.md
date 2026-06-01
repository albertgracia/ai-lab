# AI-LAB MCP Runtime Snapshot Sync ??? Dry Run

**Fase:** `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-DRY-RUN-01`
**Estado:** PASS
**HEAD base:** `c070ed33`
**Rama:** `main`

---

## 1. Objetivo

Comparar el snapshot versionado del MCP en `mcp/runtime-mcp/` contra el runtime activo real en `/mnt/mcp_server`, generando un informe de diferencias y un plan de sincronizaci??n futuro. Sin modificar nada.

---

## 2. Estado actual

| Componente | Puerto | Estado |
|---|---|---|
| `ailab-mcp-semantic-gateway` | `127.0.0.1:8091` | ??? active/enabled |
| `ailab-mcp-lan-gateway` | `0.0.0.0:8092` | ??? active/disabled |
| UFW | ??? | ??? inactive |
| Token | ??? | ??? no mostrado |

---

## 3. Validaciones

| Validaci??n | Resultado |
|---|---|
| Python compile server.py | ??? PASS |
| Python compile lan_server.py | ??? PASS |
| test_snapshot_files_exist | ??? PASS |
| test_snapshot_python_files_parse | ??? PASS |
| test_expected_tools_are_present_in_snapshot | ??? PASS |
| test_no_secret_values_are_versioned | ??? PASS |
| test_no_obvious_mutable_shell_operations | ??? PASS |
| Secret scan | ??? Limpio |

---

## 4. Comparaci??n checksum

| Archivo | Checksum MNT | Checksum REPO | Match |
|---|---|---|---|
| `server.py` | `555ca1fa...` | `555ca1fa...` | ??? |
| `lan_server.py` | `80b2230a...` | `80b2230a...` | ??? |
| `tools/__init__.py` | `a8b2690d...` | `a8b2690d...` | ??? |
| `tools/client.py` | `473dc02a...` | `473dc02a...` | ??? |
| `tools/status.py` | `fc6b6db6...` | `fc6b6db6...` | ??? |
| `tools/runtime_health.py` | `ea910e7e...` | `ea910e7e...` | ??? |
| `tools/route_preview.py` | `7f16a807...` | `7f16a807...` | ??? |
| `tools/operator.py` | `016e5f12...` | `016e5f12...` | ??? |
| `tools/incidents.py` | `90753ead...` | `90753ead...` | ??? |
| `tools/slo.py` | `1851c4d2...` | `1851c4d2...` | ??? |
| `tools/latency.py` | `53c27672...` | `53c27672...` | ??? |
| `tools/memory.py` | `fa450f15...` | `fa450f15...` | ??? |
| `config/ailab_semantic_gateway.mcp.json` | `db86964d...` | `db86964d...` | ??? |

**Todos los checksums coinciden. No hay drift entre el snapshot del repo y el runtime activo.**

### Archivos solo en MNT

| Archivo | Raz??n |
|---|---|
| `logs/.gitkeep` | No se versiona (logs excluidos) |

### Archivos solo en REPO

| Archivo | Raz??n |
|---|---|
| `README.md` | Documentaci??n repo-only |
| `SYNC-POLICY.md` | Documentaci??n repo-only |

---

## 5. Diff `server.py` y `lan_server.py`

```
diff -u /mnt/mcp_server/server.py mcp/runtime-mcp/server.py
# Sin salida ??? archivos id??nticos

diff -u /mnt/mcp_server/lan_server.py mcp/runtime-mcp/lan_server.py
# Sin salida ??? archivos id??nticos
```

**Drift detectado:** ??? No

---

## 6. Dry-run rsync

### MNT ??? REPO (??qu?? falta en el repo?)

```
deleting docs/
deleting SYNC-POLICY.md
deleting README.md
```

Resultado: solo archivos de documentaci??n repo-only se eliminar??an. El c??digo fuente coincide.

### REPO ??? MNT (simulaci??n de despliegue futuro)

```
./
```

Resultado: ning??n archivo de producci??n necesita transferencia. El snapshot est?? sincronizado.

---

## 7. Plan de sync futuro

### Prerrequisitos
- Backup de `/mnt/mcp_server` antes de cualquier sync
- Tests est??ticos pasando
- Secret scan limpio

### Flujo
```
1. cp -a /mnt/mcp_server /mnt/mcp_server.bak.$(date +%s)
2. rsync -av --delete --exclude README.md --exclude SYNC-POLICY.md --exclude docs/ \
     mcp/runtime-mcp/ /mnt/mcp_server/
3. systemctl restart ailab-mcp-semantic-gateway.service  (solo si server.py cambi??)
4. systemctl restart ailab-mcp-lan-gateway.service        (solo si lan_server.py cambi??)
5. curl -s http://127.0.0.1:8091/health
6. curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8092/health
7. Validar OpenCode local y LAN
```

### Rollback
```
rm -rf /mnt/mcp_server
cp -a /mnt/mcp_server.bak.<ts> /mnt/mcp_server
systemctl restart ailab-mcp-semantic-gateway.service
systemctl restart ailab-mcp-lan-gateway.service
```

---

## 8. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigaci??n |
|---|---|---|---|
| Drift repo vs MNT | Baja (hoy cero) | Medio | CI check pre-sync |
| Falla en sync | Baja | Alto | Backup autom??tico |
| Se olvida excluir docs | Media | Bajo | `--exclude` en script |

---

## 9. Siguiente fase recomendada

`AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-PLAN-01` ??? sincronizaci??n real del snapshot al runtime.

