---
title: "Servicios persistentes systemd"
summary: "Servicios AI-LAB configurados para arranque automático."
order: 3
---

# Servicios persistentes systemd

El AI-LAB utiliza `systemd` para mantener persistentes
los servicios críticos del laboratorio.

---

# Servicios activos

| Servicio | Función | Puerto |
|---|---|---|
| ialab-live-state | Monitorización viva del laboratorio | N/A |
| ialab-router-api | API OpenAI-compatible | 8008 |
| ialab-docs | Portal documental Astro | 4321 |

---

# Verificar estado

```bash
systemctl status ialab-live-state --no-pager

systemctl status ialab-router-api --no-pager

systemctl status ialab-docs --no-pager
