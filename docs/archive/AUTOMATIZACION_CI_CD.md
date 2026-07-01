---
title: "Automatización CI/CD — Publicación Automática de Documentación"
summary: "Sistema de publicacion automatica para ambos blogs: Cloudflare Pages para el publico y self-hosted runner para el privado."
order: 23
---

# Automatización CI/CD — Publicación Automática de Documentación

## ¿Cómo funciona?

Cuando haces `git push` a la rama `main`, ocurren dos procesos automaticos
en paralelo:

```
git push origin main
        │
        ├──[1]──→ GitHub Actions (validate)
        │               │
        │               ├── Cloudflare Pages
        │               │       │
        │               │       └── Build & Deploy → ai-lab.labrazahome.com
        │               │                           (Blog Publico)
        │               │
        │               └── Self-Hosted Runner (192.168.1.30)
        │                       │
        │                       ├── git checkout
        │                       ├── npm ci
        │                       ├── npm run build
        │                       └── systemctl restart ailab-docs.service
        │                                       │
        │                                       └── blog-ai-lab.labrazahome.com
        │                                           (Blog Privado)
        │
        └──[2]──→ El runner ejecuta el workflow deploy.yml
```

### [1] Blog Publico (Cloudflare Pages)

- GitHub notifica a Cloudflare Pages del nuevo commit
- Cloudflare Pages clona el repo y ejecuta `npm run build`
- Publica el resultado en `ai-lab.labrazahome.com`
- Tiempo total: ~1-2 minutos
- Sin intervencion manual

### [2] Blog Privado (Self-Hosted Runner)

- GitHub Actions ejecuta el job `deploy-local` en el runner local
- El runner (maquina 192.168.1.30) hace checkout del codigo
- Ejecuta `npm ci` para instalar dependencias
- Ejecuta `npm run build` para compilar Astro
- Ejecuta `sudo systemctl restart ailab-docs.service`
- El servicio `ailab-docs.service` (Astro preview en :4322) sirve la nueva version
- Tiempo total: ~20-30 segundos
- Sin intervencion manual

## Componentes del Sistema

### Workflow: `.github/workflows/deploy.yml`

```yaml
on:
  push:
    branches: [main]
    paths: ['apps/ialab-docs/**', '.github/workflows/**']

concurrency:
  group: ialab-docs-deploy
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - name: Check Python syntax
        run: python3 -m py_compile runtime/gateway/openai_gateway.py || true

  deploy-local:
    needs: validate
    runs-on: self-hosted
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm ci
        working-directory: apps/ialab-docs
      - name: Build Astro
        run: npm run build
        working-directory: apps/ialab-docs
      - name: Restart docs service
        run: sudo systemctl restart ailab-docs.service
```

### Self-Hosted Runner: `ailab-runner.service`

```bash
# /etc/systemd/system/ailab-runner.service
[Unit]
Description=GitHub Actions Runner (AI-LAB)
After=network-online.target

[Service]
Type=simple
User=albert
WorkingDirectory=/opt/ai-lab/actions-runner
ExecStart=/opt/ai-lab/actions-runner/run.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Sudoers: acceso restringido

```bash
# /etc/sudoers.d/ailab-docs
albert ALL=(root) NOPASSWD: /bin/systemctl restart ailab-docs.service
```

El runner solo puede ejecutar `systemctl restart ailab-docs.service` como root,
nada mas. La contrasena no queda almacenada en ningun lado.

## ¿Que trigger actualiza cada blog?

| Cambio | Blog Publico | Blog Privado |
|---|---|---|
| Push a `main` con cambios en `apps/ialab-docs/` | ✅ Automatico (Cloudflare) | ✅ Automatico (Runner) |
| Push a `main` sin cambios en docs | ❌ No se activa | ❌ No se activa |
| Workflow manual (GitHub Actions UI) | ❌ No se activa | ✅ Manual |

## Archivos del proyecto

| Archivo | Proposito |
|---|---|
| `.github/workflows/deploy.yml` | Workflow de CI/CD |
| `/etc/systemd/system/ailab-runner.service` | Servicio del runner |
| `/etc/sudoers.d/ailab-docs` | Permiso sudo limitado |
| `/opt/ai-lab/actions-runner/` | Directorio del runner |
| `.gitignore` | Excluye `actions-runner/` |

## Comandos de gestion

```bash
# Ver estado del runner
systemctl status ailab-runner.service

# Ver logs del runner
journalctl -u ailab-runner.service -n 50 --no-pager

# Ver logs del build
journalctl -u ailab-runner.service | grep -E 'Job|Running|Finish'

# Reiniciar runner
systemctl restart ailab-runner.service

# Ver ultimo build en el blog privado
curl -s http://localhost:4322/ | head -1
```

## Verificacion de funcionamiento

Para validar que todo funciona correctamente:

```bash
# 1. Hacer un cambio en un documento
echo "test" >> apps/ialab-docs/src/content/docs/almacenamiento-ai-lab.md

# 2. Commit y push
git add -A && git commit -m "test: verificacion CI/CD" && git push origin main

# 3. Verificar en GitHub Actions que el job se ejecuta
#    https://github.com/albertgracia/ai-lab/actions

# 4. Esperar y verificar ambos blogs
#    Blog publico:  curl -s https://ai-lab.labrazahome.com/ | head -1
#    Blog privado:  curl -s http://localhost:4322/ | head -1
```
