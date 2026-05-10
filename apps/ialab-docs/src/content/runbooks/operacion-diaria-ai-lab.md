---
title: "Operación diaria AI-LAB"
summary: "Checklist básico para comprobar que el laboratorio está operativo."
severity: "info"
---

# Operación diaria AI-LAB

Checklist básico para validar el estado del laboratorio.

## 1. Comprobar servicios systemd

```bash
systemctl status ialab-live-state --no-pager
systemctl status ialab-router-api --no-pager
systemctl status ialab-docs --no-pager
