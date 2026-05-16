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
