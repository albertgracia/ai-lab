# AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01 — Auditoría

**Resultado:** PARTIAL
**HEAD base:** 0a609cd1
**HEAD final:** <pendiente commit>
**Rama:** main
**Fecha:** 2026-06-01

---

## 1. Resumen

Smoke tests del endpoint LAN `8092` completados desde servidor local y `192.168.1.50` (X870EAORUSPRO). No se pudo probar desde `192.168.1.250` (NAS-N5 / LM Studio) por falta de acceso SSH. `8091` intacto.

---

## 2. Estado

| Componente | Estado |
|---|---|
| 8091 | `active (running)`, `127.0.0.1:8091` |
| 8092 | `active (running)`, `0.0.0.0:8092`, disabled |
| UFW | `inactive` (no modificado) |
| Token fingerprint | `ff4f2df5ea199879` |

---

## 3. Pruebas

| Origen | Sin token | Con token | Resultado |
|---|---|---|---|
| Servidor local (127.0.0.1) | 401 ✅ | 404/406 ✅ | PASS |
| Servidor LAN (192.168.1.30) | — | 404/406 ✅ | PASS |
| 192.168.1.50 (X870EAORUSPRO) | 401 ✅ | 404/406 ✅ | PASS |
| 192.168.1.250 (NAS-N5 / LM Studio) | ❌ No accesible | ❌ No accesible | PENDIENTE |

---

## 4. Tools

- AI-LAB Runtime: 8 tools read-only visibles en OpenCode local (confirmado en fases previas)
- GitNexus: 14 tools — no se probaron desde LAN (no necesario para este smoke)

---

## 5. Causa de PARTIAL

No se pudo acceder a `192.168.1.250` (NAS-N5) vía SSH (timeout en puertos 22 y 2222). El smoke desde LM Studio queda pendiente para el operador.

---

## 6. Cambios en repo

- `docs/mcp/AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01.md` (creado)
- `docs/audits/AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01.md` (creado)

**Commit local:** Sí
**Push:** No
**Tag:** No

---

## 7. Confirmaciones

| Confirmación | Sí/No |
|---|---|
| 8091 intacto | ✅ |
| OpenCode no modificado | ✅ |
| Runtime no tocado | ✅ |
| UFW no modificado | ✅ |
| Token no filtrado | ✅ |
| Sin push | ✅ |
| Sin tag | ✅ |

---

## 8. Siguientes fases

1. `AI-LAB-LMSTUDIO-MCP-LAN-SMOKE-01` (reintento por operador)
2. `AI-LAB-MCP-LAN-SMOKE-PUSH-01`
3. `AI-LAB-MCP-CONTROL-PLANE-REPO-UNIFICATION-01`
