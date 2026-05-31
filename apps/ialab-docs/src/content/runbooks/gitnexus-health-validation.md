---
title: "GitNexus Health Validation"
summary: "Validación mínima de resiliencia GitNexus: proceso, puerto, /api/health, stats nodes/edges, y recuperación."
---


## Validación mínima

```bash
curl -s http://127.0.0.1:4747/api/health
curl -s http://127.0.0.1:4747/api/repos | jq '.[0].stats | {nodes,edges,communities,processes}'
```

## Script

```bash
/opt/ai-lab/scripts/gitnexus-health.sh
```

## Nota: si no hay systemd

Si GitNexus no está gestionado por `systemd` todavía, puede levantarse manualmente:

```bash
nohup npx --yes gitnexus@latest serve --host 0.0.0.0 --port 4747 </dev/null >/tmp/gitnexus-serve.log 2>&1 & disown
```

## Señales de fallo

- `Waiting for server to start` en UI.
- `/api/health` no responde.
- `nodes==0` o `edges==0`.

## Recovery rápido

Ver:

- `/runbooks/gitnexus-service-recovery`
