---
title: "Cloudflare Pages — Redirects y Submodules"
summary: "Solucion a los problemas de build en Cloudflare Pages: submodules git y redirects externos no soportados."
order: 21
---

# Cloudflare Pages — Problemas de Build y Soluciones

## Problema 1: Submodules de Git

**Sintoma:** El build fallaba con:
```
fatal: No url found for submodule path 'stacks/websites/agithome' in .gitmodules
Failed: error occurred while updating repository submodules
```

**Causa:** Cloudflare Pages ejecuta `git clone --recurse-submodules` y las carpetas
bajo `stacks/websites/` (agithome, agitservices, albertskills, etc.) tenian directorios
`.git` residuales que Cloudflare interpretaba como submodules.

**Solucion:**
1. Eliminar los directorios `.git` de cada subcarpeta
2. Crear un archivo `.gitmodules` vacio en la raiz del repo
3. Commit y push para forzar rebuild

```bash
# Remover .git de las subcarpetas
find stacks -name '.git' -type d -exec rm -rf {} + 2>/dev/null

# Crear .gitmodules vacio
echo '' > .gitmodules
git add -f .gitmodules
git commit -m "fix: add empty .gitmodules for Cloudflare Pages"
git push
```

**Resultado:** Build exitoso sin errores de submodules.

## Problema 2: Redirects Externos no Soportados

**Sintoma:** Warning en el log de build:
```
Found invalid redirect lines:
  - #3: /api/* https://blog-ai-lab.labrazahome.com/api/:splat 200
    Proxy (200) redirects can only point to relative paths.
```

**Causa:** El archivo `public/_redirects` contenia una regla de proxy (status 200)
a una URL externa. Cloudflare Pages solo permite proxy redirects a rutas relativas
dentro del mismo sitio.

**Solucion:** Eliminar la regla de redirect a URL externa. El API solo esta
disponible a traves del blog privado (Traefik), no desde el sitio publico.

```bash
rm apps/ialab-docs/public/_redirects
```

**Alternativa:** Si se necesita el API en el sitio publico, usar un redirect
302 (sin proxy) o configurar un Cloudflare Worker para el proxy.

## Lecciones Aprendidas

1. Cloudflare Pages no soporta `200` (proxy) redirects a URLs externas
2. Las carpetas con `.git` internos son detectadas como submodules
3. Un `.gitmodules` vacio previene errores de inicializacion
4. Siempre verificar los logs de build en Cloudflare Pages dashboard
