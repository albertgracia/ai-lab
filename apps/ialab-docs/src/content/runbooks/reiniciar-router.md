---
title: "Reiniciar AI-LAB Router"
summary: "Procedimiento seguro para reiniciar el router OpenAI-compatible."
severity: "medium"
---

# Reiniciar AI-LAB Router

## Procedimiento manual

```bash
cd /opt/ai-lab
source .venv/bin/activate
export PYTHONPATH=/opt/ai-lab

uvicorn runtime.llm.router_api:app --host 0.0.0.0 --port 8008

