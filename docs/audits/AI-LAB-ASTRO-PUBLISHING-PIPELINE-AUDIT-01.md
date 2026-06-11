# AI-LAB-ASTRO-PUBLISHING-PIPELINE-AUDIT-01

**Estado:** PASS  
**Fecha:** 2026-06-11  
**Fase:** AI-LAB-ASTRO-PUBLISHING-PIPELINE-AUDIT-01  
**Modo:** READ-ONLY  
**Tag:** — (pre-commit)

---

## HARD_FACTS

### 1. Git state (local SMB mount — `E:\opencode\ai-lab`)

| Dato | Valor |
|------|-------|
| HEAD commit | `ecb9bd68` `chore: update public metrics [skip ci]` |
| Rama activa | `main` |
| origin/main | `ecb9bd68` (idéntico a HEAD) |
| AHEAD of origin | **0** commits |
| BEHIND origin | **0** commits |
| Working tree | **DIRTY** — 8 modified + 13 untracked files |
| Último commit mensaje | Contiene `[skip ci]` |

**Ninguno de los cambios Astro actuales ha sido commiteado ni pusheado.**

### 2. Archivos no commiteados (contenido Astro nuevo)

```
M apps/ialab-docs/astro.config.mjs
M apps/ialab-docs/src/content/docs/architecture/index.md
M apps/ialab-docs/src/content/docs/governance/index.md
M apps/ialab-docs/src/content/docs/grounding-y-rag.md
M apps/ialab-docs/src/content/docs/index.md
?? apps/ialab-docs/src/content/blog/017-anythingllm-memoria-documental.md
?? apps/ialab-docs/src/content/docs/architecture/anythingllm-role.md
?? apps/ialab-docs/src/content/docs/architecture/cognitive-health-layer.md
?? apps/ialab-docs/src/content/docs/governance/anythingllm-reindex-automation.md
?? apps/ialab-docs/src/content/docs/governance/phase-closure-protocol.md
```

### 3. Build local (SMB mount)

| Resultado | Detalle |
|-----------|---------|
| `npm run build` | **PASS** — 264 páginas, 0 errores |
| `dist/blog/017-anythingllm-memoria-documental/index.html` | ✅ Existe |
| `dist/docs/architecture/anythingllm-role/index.html` | ✅ Existe |
| `dist/docs/governance/anythingllm-reindex-automation/index.html` | ✅ Existe |

### 4. Sitio público (`ai-lab.labrazahome.com`)

| Dato | Valor |
|------|-------|
| Stack | Cloudflare Pages → GitHub (`albertgracia/ai-lab`) |
| Rama | `main` |
| Build command | `npm run build` (root: `apps/ialab-docs`) |
| Output dir | `dist` |
| Último commit desplegado | `ecb9bd68` (o anterior) |
| `GET /blog/017-anythingllm-memoria-documental/` | **404** — no existe |
| `GET /` | **200** — contenido antiguo |

**Conclusión público:** no hay cambios nuevos en GitHub → Cloudflare Pages no tiene nada nuevo que desplegar.

### 5. Sitio privado (`blog-ai-lab.labrazahome.com`)

| Dato | Valor |
|------|-------|
| Stack | Cloudflare Access → Traefik → `ailab-docs` (:4322) |
| `ailab-docs` servicio | `astro preview --host 0.0.0.0 --port 4322` |
| Sirve desde | `/opt/ai-lab/apps/ialab-docs/dist/` |
| `GET /` | **200** (Cloudflare Access login → contenido) |
| Repo productivo | `/opt/ai-lab` (servidor Ubuntu .30) |

**Conclusión privado:** el servicio `ailab-docs` en `.30` sirve desde `/opt/ai-lab`, NO desde `E:\opencode\ai-lab` (SMB). El build local en SMB no afecta al sitio privado.

### 6. Arquitectura de despliegue (fuente: `ASTRO-DEPLOYMENT-GOVERNANCE.md`)

| Sitio | Pipeline | Trigger |
|-------|----------|---------|
| **Público** | `git push → GitHub → Cloudflare Pages build → deploy` | Commit + push a `main` |
| **Privado** | `npm run build → sudo systemctl restart ailab-docs` | Comando manual en `.30` |

### 7. `[skip ci]` en HEAD commit

El commit `ecb9bd68` contiene `[skip ci]`. Cloudflare Pages reconoce `[skip ci]` y `[skip cd]` en mensajes de commit y **omite el despliegue automático**. Aunque hubiera cambios, este commit en particular no desencadenó build.

---

## UNKNOWNS

| Incógnita | Estado |
|-----------|--------|
| ¿`/opt/ai-lab` en `.30` es el mismo repo o mount SMB? | **NO DISPONIBLE** — no se puede verificar sin acceso SSH |
| ¿Está `ailab-docs` corriendo en `.30`? | **NO DISPONIBLE** — READ-ONLY, no se verifica servicio |
| ¿Qué commit tiene desplegado el privado? | **NO DISPONIBLE** — el acceso requiere Cloudflare Zero Trust (login Google) |
| ¿`/opt/ai-lab` tiene cambios divergentes del SMB? | **NO DISPONIBLE** — no se puede comparar remoto |
| ¿Traefik tiene configuraciones adicionales? | Documentado en `/opt/ai-lab/stacks/traefik/` — no accesible desde aquí |

---

## ROOT_CAUSE

**Causa raíz única: los cambios Astro nunca fueron commiteados ni pusheados.**

El flujo de publicación para ambos sitios requiere un paso que no se ejecutó:

| Sitio | Paso faltante |
|-------|---------------|
| **Público** | `git add → git commit → git push` a `origin main` |
| **Privado** | `npm run build` en `/opt/ai-lab` + `sudo systemctl restart ailab-docs` |

El `dist/` generado localmente en `E:\opencode\ai-lab\apps\ialab-docs\dist\`:
- **No afecta** al sitio público (Cloudflare Pages construye su propio `dist/` desde GitHub)
- **No afecta** al sitio privado (el servicio `ailab-docs` en `.30` sirve desde `/opt/ai-lab/apps/ialab-docs/dist/`)

Además, el commit `ecb9bd68` en HEAD tiene `[skip ci]`, que Cloudflare Pages interpreta como "no ejecutar CI/CD". Esto no bloquea commits futuros (cada commit se evalúa independientemente), pero significa que el último push no generó deploy.

---

## RISK

| Riesgo | Nivel | Detalle |
|--------|-------|---------|
| Pérdida de cambios no commiteados | **ALTO** | 13 untracked + 8 modified solo en working tree SMB |
| Drift entre repos SMB y `.30` | **ALTO** | No se puede verificar; pueden divergir |
| `[skip ci]` en commits futuros | **BAJO** | Fácil de evitar: no incluir en mensajes de contenido |
| Cloudflare Access bloquea verificación | **MEDIO** | No se puede confirmar estado del privado sin login |

---

## RECOMMENDED_FIX_PHASE

Se requiere una fase futura (FUERA DEL ALCANCE READ-ONLY) para resolver:

### Fase propuesta: ASTRO-PUBLISHING-DEPLOY-01

**Pasos:**

1. **Commit + Push** (para sitio público):
   ```bash
   git add apps/ialab-docs/
   git commit -m "feat(docs): FASE PC-01, 37A, anythingllm-reindex-automation, blog 017"
   git push origin main
   ```
   → Cloudflare Pages detecta push → build → deploy automático.

2. **Build + Restart** (para sitio privado, en `.30`):
   ```bash
   ssh albert@192.168.1.30
   cd /opt/ai-lab
   git pull origin main
   cd apps/ialab-docs
   npm run build
   sudo systemctl restart ailab-docs
   curl -I http://127.0.0.1:4322/
   ```

3. **Verificación**:
   - `curl -I https://ai-lab.labrazahome.com/blog/017-anythingllm-memoria-documental/` → 200
   - `curl -I https://blog-ai-lab.labrazahome.com/docs/governance/anythingllm-reindex-automation/` → 200 (autenticado)

## Conclusión

**PASS — Causa identificada con evidencia.**
No se requiere cambio operativo. Los cambios existen localmente pero no han sido publicados porque el pipeline de publicación requiere commit+push (público) y build+restart (privado), y ninguno de los dos pasos se ejecutó.
