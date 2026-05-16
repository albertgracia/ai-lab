## Pre-commit hook — Astro build check

Antes de cualquier commit que toque `apps/ialab-docs/`, ejecuta `npm run build` automáticamente. Si el build falla, el commit se bloquea.

### Setup (una vez por clon)

```bash
ln -sf ../../scripts/pre-commit.sh .git/hooks/pre-commit
```

### Bypass

```bash
git commit --no-verify
```

## Regla: despliegue de documentación Astro

Cada vez que crees o modifiques documentación en `apps/ialab-docs/src/content/docs/`:

1. **Espera al pre-commit hook** — ya hace build + restart automáticamente
2. Si haces build manual (sin commit), ejecuta también:
   ```bash
   echo 19682507 | sudo -S systemctl restart ailab-docs
   ```
3. Verifica con `curl http://localhost:4322/docs/<slug>/` (debe dar 200)
4. El público (`ai-lab.labrazahome.com`) se despliega solo desde GitHub

El pre-commit hook ya lo hace automático en cada commit que toque docs.

## Servicios activos

| Servicio | Puerto | URL |
|---|---|---|
| `ailab-docs` | 4322 | blog-ai-lab.labrazahome.com (privado) |
| `ailab-metrics` | 3010 | metricas.labrazahome.com (privado, Next.js SSR) |
| `ailab-router` | 8083 | API router |
| `ailab-live-api` | 8084 | API datos en vivo |
