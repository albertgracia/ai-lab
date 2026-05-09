# AI-LAB CONTEXT

You are operating inside Albert's local AI-Lab infrastructure.

Always respond in Spanish unless explicitly requested otherwise.

## Environment

Main Linux node:
- Hostname: ubuntu-ialab
- IP: 192.168.1.30
- Project root: /opt/ai-lab

Windows GPU nodes:
- Gaming PC RX9070XT
  - IP: 192.168.1.50
  - Hostname: X870EAORUSPRO
  - SSH user: ailab
  - VRAM: 16 GB

- Gaming PC RX7900XT
  - IP: 192.168.1.60
  - Hostname: X870AORUSELITE
  - SSH user: ailab
  - VRAM: 20 GB

## Core services

Docker services:
- traefik
- qdrant
- open-webui
- ollama
- portainer

Runtime:
- runtime/state/system_state.py
- runtime/state/gpu_state.py
- runtime/llm/model_router.py
- runtime/llm/invoke.py

## Rules

Never invent files, ports, services, logs, or configuration.
Use runtime state as source of truth.
Prefer safe diagnostics before proposing changes.
Do not restart, delete, overwrite, or modify infrastructure without explicit confirmation.
Always distinguish FACT from HYPOTHESIS.
For code changes, explain target file and expected effect.
For infra changes, include rollback.
