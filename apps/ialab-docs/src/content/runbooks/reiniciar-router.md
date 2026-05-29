---
title: "Reiniciar AI-LAB Router"
summary: "Procedimiento seguro para reiniciar el router OpenAI-compatible."
severity: "medium"
---

## Procedimiento manual

```bash
cd /opt/ai-lab
source .venv/bin/activate
export PYTHONPATH=/opt/ai-lab

uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8083
```

> **Nota:** No usar `ialab-router-api.service`; fue eliminado como unidad duplicada/remanente.
> El servicio activo es `ailab-router.service` en el puerto 8083.
