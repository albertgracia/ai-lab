---
title: "GitNexus Service Recovery"
summary: "Recuperación del servicio GitNexus: health, restart seguro, conflictos de puerto y verificación de index cargado."
---


## Health rápido

```bash
curl -s http://127.0.0.1:4747/api/health
curl -s http://127.0.0.1:4747/api/repos | jq '.[0].stats'
```

Esperado:

- `/api/health` → `{"status":"ok"}`
- `/api/repos` → `nodes > 0` y `edges > 0`

## Si el puerto 4747 no responde

1. Ver listener:

```bash
ss -tlnp | grep ':4747'
```

2. Reiniciar service (si existe):

```bash
sudo systemctl restart gitnexus
sudo systemctl status gitnexus --no-pager
```

## Conflicto de puerto

Si `gitnexus` no arranca por “address already in use”, hay un proceso manual ocupando `:4747`.

```bash
ss -tlnp | grep ':4747'
# matar PID manual solo si es el gitnexus antiguo
kill <pid>
sudo systemctl restart gitnexus
```

## Verificación final

```bash
/opt/ai-lab/scripts/gitnexus-health.sh
```
