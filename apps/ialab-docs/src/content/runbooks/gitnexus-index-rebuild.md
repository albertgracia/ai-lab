---
title: "GitNexus Index Rebuild"
summary: "Rebuild seguro del índice GitNexus: cuándo forzar, cómo validar, y qué NO indexar (runtime/state)."
---


## Cuándo hacer rebuild

- Index stale.
- Cambios estructurales grandes en `runtime/`.
- Síntomas: UI sin datos, repos sin stats.

## Rebuild (safe)

Desde `/opt/ai-lab`:

```bash
npx gitnexus status
npx gitnexus analyze --force --index-only --skip-agents-md --no-stats
npx gitnexus status
```

## Validación

```bash
curl -s http://127.0.0.1:4747/api/repos | jq '.[0].stats | {nodes,edges,processes}'
```

## Governance

- `.gitnexusignore` debe excluir `runtime/state/*`.
- No usar embeddings por defecto salvo necesidad explícita.
