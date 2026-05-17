---
title: "Runbook — Cloudflare Pages y Sincronizacion"
summary: "Problemas comunes con Cloudflare Pages y sus soluciones: submodules git, redirects, builds fallidos, sincronizacion."
order: 21
---

# Runbook — Cloudflare Pages y Sincronizacion

## Indice de Problemas

| # | Problema | Sintoma | Solucion |
|---|---|---|---|
| 1 | Submodules git | `No url found for submodule path` | Crear `.gitmodules` vacio |
| 2 | Redirects externos | `Proxy (200) redirects can only point to relative paths` | Eliminar regla `_redirects` |
| 3 | Build fallido sin cambios | Sin deploy nuevo tras push | Verificar `.gitmodules` y submodules |
| 4 | Contenido desactualizado | Pagina no muestra ultimos docs | Rebuild local + push a GitHub |
| 5 | 404 pagina nueva | Doc creado pero no accesible | Commit + push + esperar build |

---

## Problema 1: Submodules Git

**Sintoma:**
```
fatal: No url found for submodule path 'stacks/websites/agithome' in .gitmodules
Failed: error occurred while updating repository submodules
```

**Causa:** Carpetas bajo `stacks/websites/` tienen directorios `.git` residuales.
Cloudflare Pages ejecuta `git clone --recurse-submodules` y detecta estas
carpetas como submodules, pero no hay `.gitmodules` que defina sus URLs.

**Solucion:**

```bash
# 1. Eliminar los .git de las subcarpetas
find /opt/ai-lab/stacks/websites -name '.git' -type d -exec rm -rf {} + 2>/dev/null

# 2. Crear .gitmodules vacio en la raiz del repo
cd /opt/ai-lab
echo '' > .gitmodules

# 3. Commit y push
git add -f .gitmodules
git commit -m "fix: add empty .gitmodules for Cloudflare Pages"
git push origin main
```

**Verificacion:** El siguiente build de Cloudflare Pages no debe mostrar errores
de submodules.

---

## Problema 2: Redirects Externos

**Sintoma:**
```
Found invalid redirect lines:
  - /api/* https://blog-ai-lab.labrazahome.com/api/:splat 200
    Proxy (200) redirects can only point to relative paths.
```

**Causa:** El archivo `public/_redirects` contiene una regla de proxy (status 200)
a una URL externa. Cloudflare Pages solo permite proxy redirects a rutas
relativas dentro del mismo sitio.

**Solucion:**

```bash
# Eliminar el archivo _redirects
rm /opt/ai-lab/apps/ialab-docs/public/_redirects
rm -f /opt/ai-lab/apps/ialab-docs/dist/_redirects

# Commit y push
cd /opt/ai-lab
git add -f apps/ialab-docs/public/_redirects
git commit -m "fix: remove _redirects with unsupported external proxy rule"
git push origin main
```

**Nota:** Sin el `_redirects`, el API `/api/*` no esta disponible en el sitio
publico. Solo funciona en el blog privado via Traefik.

---

## Problema 3: Build Fallido sin Causa Visible

**Sintoma:** Un push a GitHub no genera un nuevo deploy en Cloudflare Pages,
o el build falla sin un error claro.

**Causa:** El build de Cloudflare Pages depende de varios factores:
- Submodules git no configurados
- Missing `site` en `astro.config.mjs`
- Vite/Node version incompatible
- Schema de contenido de Starlight

**Solucion:**

```bash
# 1. Verificar el log de build en Cloudflare Dashboard
#    Ir a Workers & Pages -> ai-lab -> ultimo deploy

# 2. Errores comunes:
#    - InvalidContentEntryDataError: Schema de frontmatter incorrecto
#    - Missing site config: anadir site a astro.config.mjs

# 3. Build local para diagnosticar
cd /opt/ai-lab/apps/ialab-docs
npm run build 2>&1 | grep -i error

# 4. Forzar rebuild con un commit vacio
git commit --allow-empty -m "chore: trigger rebuild"
git push origin main
```

---

## Problema 4: Contenido No Actualizado

**Sintoma:** El blog muestra contenido antiguo. Los nuevos documentos no
aparecen.

**Causa:** El blog publico depende del build de Cloudflare Pages. El blog
privado depende del runner local, que ejecuta build + restart al detectar un
push; si eso falla, la correccion manual es build + restart del servicio.

**Soluciones:**

### Para el blog publico:
```bash
# 1. Verificar que los cambios estan en GitHub
git status
git push origin main

# 2. Esperar 1-2 min a que Cloudflare Pages termine el build

# 3. Forzar recarga del navegador: Ctrl+F5 o Cmd+Shift+R
```

### Para el blog privado:
```bash
# 1. Rebuild local
cd /opt/ai-lab/apps/ialab-docs && npm run build

# 2. Reiniciar servicio
echo 19682507 | sudo -S systemctl restart ailab-docs.service

# 3. Forzar recarga del navegador: Ctrl+F5
```

---

## Problema 5: Pagina 404 Tras Crear Nuevo Documento

**Sintoma:** Se crea un nuevo `.md` en `src/content/docs/`, se hace commit y push,
pero la pagina devuelve 404.

**Causa:** El documento existe en GitHub pero Cloudflare Pages aun no ha
completado el build (tarda ~1-2 min). Si el blog privado tambien falla, el
runner local puede no haber terminado su build/restart o puede requerir una
intervencion manual.

**Solucion:**

```bash
# 1. Verificar que el archivo existe en GitHub
#    Ir a https://github.com/albertgracia/ai-lab/tree/main/apps/ialab-docs/src/content/docs/

# 2. Esperar el build de Cloudflare Pages (~2 min)

# 3. Si el blog privado tambien da 404, rebuild local:
cd /opt/ai-lab/apps/ialab-docs && npm run build
echo 19682507 | sudo -S systemctl restart ailab-docs.service

# 4. Forzar recarga del navegador
```

---

## Comandos Rapidos

```bash
# Build + deploy completo (ambos blogs)
cd /opt/ai-lab/apps/ialab-docs && npm run build && \
  echo 19682507 | sudo -S systemctl restart ailab-docs.service && \
  cd /opt/ai-lab && git add -A && git commit -m "docs: actualizacion" && \
  git push origin main

# Verificar estado del blog privado
curl -s http://localhost:4322/ | head -1

# Verificar estado del blog publico
curl -s https://ai-lab.labrazahome.com/ | head -1
```
