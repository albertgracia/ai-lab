# AI-LAB-MCP-RUNTIME-METRICS-ROLLBACK-01

## Resultado: **PASS**

| Campo | Valor |
|---|---|
| **Fecha** | 2026-06-07 11:58 UTC |
| **Ejecutor** | `albert@ubuntu-ialab` |
| **HEAD** | `84dda79f` |
| **Rama** | `main` |
| **Git status** | `main...origin/main [ahead 1, behind 5]` |
| **Working tree** | Clean (solo cambios permitidos tras esta fase) |

---

## 1. Backup usado

```
/home/albert/backups/ai-lab/mcp-runtime-apply/20260606-210855/mcp_server
```

## 2. Rollback script usado

```
/tmp/rollback-mcp-runtime-metrics-apply.sh
```

---

## 3. Resumen del fallo (APPLY)

La fase `AI-LAB-MCP-RUNTIME-SNAPSHOT-SYNC-APPLY-01` aplicó 4 archivos al runtime real (`/mnt/mcp_server`):

- `server.py`
- `lan_server.py`
- `metrics.py`
- `tools/__init__.py`

Síntomas:

| Síntoma | Detalle |
|---|---|
| **Timeout en 8092 /mcp** | `GET /mcp` sin token + `Accept: text/event-stream` timeout |
| **LAN 404** | Logs LAN mostraron `GET /mcp 404` desde `192.168.1.50` |
| **ASGI warning** | `ASGI callable returned without completing response` |
| **OpenCode** | Rojo (desconectado) |
| **LM Studio** | Dejó de conectar correctamente |

---

## 4. Resumen del rollback

- Rollback ejecutado **antes** de esta fase de auditoría.
- Script usado: `/tmp/rollback-mcp-runtime-metrics-apply.sh`
- Backup restaurado desde: `/home/albert/backups/ai-lab/mcp-runtime-apply/20260606-210855/mcp_server`
- Servicios reiniciados por el rollback: `ailab-mcp-semantic-gateway`, `ailab-mcp-lan-gateway`

Recuperación confirmada:

| Componente | Estado |
|---|---|
| **8091 (semantic)** | ✅ active/enabled |
| **8092 (LAN)** | ✅ active/enabled |
| **LM Studio** | ✅ Operador confirmó funcionamiento |
| **OpenCode** | ✅ Verde (reconectado) |

---

## 5. Estado endpoints (post-rollback)

| Endpoint | Respuesta | Esperado |
|---|---|---|
| `8091 /mcp` | `406 Not Acceptable` | ✅ Correcto |
| `8092 /mcp` sin token | `401 Unauthorized` | ✅ Correcto |
| `8092 /mcp` sin token + SSE | `401 Unauthorized` | ✅ Correcto |
| `8091 /metrics` | `404 Not Found` | ✅ Métricas runtime revertidas |
| `8092 /metrics` sin token | `401 Unauthorized` | ✅ Correcto |

No hay timeouts. Los endpoints responden correctamente.

---

## 6. Estado servicios

| Servicio | Enabled | Active | Puerto |
|---|---|---|---|
| `ailab-mcp-semantic-gateway` | `enabled` | `active` (PID 1573) | `127.0.0.1:8091` |
| `ailab-mcp-lan-gateway` | `enabled` | `active` (PID 1568) | `0.0.0.0:8092` |

Ambos servicios activos desde `2026-06-07 11:37:14 CEST`.

Tráfico LAN normal desde `192.168.1.50` (POST/GET `/mcp` → `200 OK`).

---

## 7. Tests

```text
10 passed in 0.03s
```

- `tests/test_mcp_runtime_snapshot_01.py` ✅
- `tests/test_mcp_runtime_metrics_01.py` ✅

Tests sobre repo snapshot pasan correctamente. No afectados por rollback runtime.

---

## 8. Secret scan

Limpio. Solo placeholders de test en `tests/test_mcp_runtime_snapshot_01.py` (`BEGIN RSA`, `BEGIN OPENSSH`, etc.) y referencias en docs existentes. No hay secretos reales expuestos.

---

## 9. Sudo state

```
SUDO_LOCKED
```

El comando `sudo -n true` devuelve error de autenticación interactiva. Sudo bloqueado correctamente.

---

## 10. Token

- **No leído.**
- **No mostrado.**
- No se accedió a `/etc/ai-lab/mcp-lan.env`.
- No se accedió a token real en logs.

---

## 11. Prometheus / Grafana

- **No tocados.**
- No se ejecutó configuración de Prometheus rules.
- No se accedió a dashboards de Grafana.
- No se modificó configuración real de Prometheus.

---

## 12. UFW / Firewall

- **No tocado.**

---

## 13. Runtime

- El rollback ya fue ejecutado **antes** de esta fase.
- Esta fase **no modificó runtime** (`/mnt/mcp_server`).
- No se ejecutó `systemctl restart`.
- No se modificaron archivos en `mcp/runtime-mcp`.
- No se modificaron systemd units.

---

## 14. Logs

- **Semantic (8091):** Sin errores tras rollback. `406` esperado en `/mcp`, `404` en `/metrics`.
- **LAN (8092):** Tráfico normal desde `.50`. Sin errores ASGI en la sesión actual.
- Los warnings `ASGI callable returned without completing response` aparecen en sesiones anteriores (stop graceful de systemd), no en runtime actual.

---

## 15. Conclusión

- **Runtime metrics APPLY queda revertido.**
- **Prometheus implementation pausada.**
- **No continuar Prometheus hasta corregir LAN.**

El sistema se encuentra en estado estable:

- Ambos gateways operativos.
- Clientes (OpenCode, LM Studio) funcionando.
- Sin secretos expuestos.
- Sin cambios operativos en esta fase.
- Sudo bloqueado.
- Commit local creado (sin push).

---

## 16. Siguiente fase recomendada

1. **`AI-LAB-MCP-LAN-ASGI-404-TRIAGE-01`**: Investigar por qué la versión metrics del `lan_server.py` provocaba timeout/404 en `/mcp` con token.
2. Tras corregir LAN, diseñar nueva implementación **repo-only** de métricas runtime.
3. Probar en staging/snapshot antes de cualquier APPLY a runtime real.
